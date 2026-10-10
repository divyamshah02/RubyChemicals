from django.db import transaction
from django.http import HttpResponse
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from UserDetail.models import ActivityLog
from utils.create_coa_pdf import format_date, generate_coa
from utils.decorators import check_authentication, handle_exceptions

from .models import ProductionBatch, StockItem, StockItemParameter
from .serializers import StockItemParameterSerializer


def _error(message, status):
    return Response({
        "success": False,
        "user_not_logged_in": False,
        "user_unauthorized": False,
        "data": None,
        "error": message,
    }, status=status)


class StockItemParameterViewSet(viewsets.ViewSet):
    """Quality parameters (COA table rows) for a stock item."""

    @handle_exceptions
    @check_authentication()
    def list(self, request):
        stock_item_id = request.query_params.get("stock_item")
        if not stock_item_id:
            return _error("stock_item is required", 400)

        try:
            item = StockItem.objects.get(pk=stock_item_id)
        except (StockItem.DoesNotExist, ValueError):
            return _error("Stock item not found", 404)

        parameters = StockItemParameter.objects.filter(stock_item=item)
        return Response({
            "success": True,
            "user_not_logged_in": False,
            "user_unauthorized": False,
            "data": {
                "stock_item": {"id": item.id, "name": item.name},
                "parameters": StockItemParameterSerializer(parameters, many=True).data,
            },
            "error": None,
        }, status=200)

    @action(detail=False, methods=["post"], url_path="bulk-save")
    @handle_exceptions
    @check_authentication(required_role="admin")
    def bulk_save(self, request):
        """Replaces every parameter of a stock item with the submitted ordered list."""
        stock_item_id = request.data.get("stock_item")
        rows = request.data.get("parameters")

        if not stock_item_id or not isinstance(rows, list):
            return _error("stock_item and parameters list are required", 400)

        try:
            item = StockItem.objects.get(pk=stock_item_id)
        except (StockItem.DoesNotExist, ValueError):
            return _error("Stock item not found", 404)

        cleaned = []
        for row in rows:
            particulars = str(row.get("particulars", "")).strip()
            parameter = str(row.get("parameter", "")).strip()
            result = str(row.get("result", "")).strip() or "PASSES"
            if not particulars and not parameter:
                continue
            if not particulars:
                return _error("Particulars is required for every parameter row", 400)
            cleaned.append((particulars, parameter, result))

        with transaction.atomic():
            StockItemParameter.objects.filter(stock_item=item).delete()
            StockItemParameter.objects.bulk_create([
                StockItemParameter(
                    stock_item=item,
                    particulars=particulars,
                    parameter=parameter,
                    result=result,
                    sort_order=index,
                )
                for index, (particulars, parameter, result) in enumerate(cleaned)
            ])

        ActivityLog.objects.create(
            user=request.user,
            action="UPDATE",
            model_name="StockItemParameter",
            record_id=str(item.id),
            description=f"Saved {len(cleaned)} COA parameters for stock item {item.name}",
        )

        parameters = StockItemParameter.objects.filter(stock_item=item)
        return Response({
            "success": True,
            "user_not_logged_in": False,
            "user_unauthorized": False,
            "data": StockItemParameterSerializer(parameters, many=True).data,
            "error": None,
        }, status=200)


class DownloadCOAViewSet(viewsets.ViewSet):
    """Generates the Certificate of Analysis PDF for a production batch."""

    @handle_exceptions
    @check_authentication()
    def retrieve(self, request, pk=None):
        try:
            batch = ProductionBatch.objects.select_related(
                "product", "production_card"
            ).get(pk=pk, is_active=True)
        except (ProductionBatch.DoesNotExist, ValueError):
            return _error("Production batch not found", 404)

        product = batch.product
        parameters = list(
            StockItemParameter.objects.filter(stock_item=product).values(
                "particulars", "parameter", "result"
            )
        )
        if not parameters:
            return _error(
                f"Parameters not added for \"{product.name}\". "
                "Please add them from the Stock Items page before generating the COA.",
                400,
            )

        card = batch.production_card
        production_date = card.production_date if card else batch.created_at.date()
        formatted_date = format_date(production_date)

        stream = generate_coa(
            ref_no=batch.batch_code,
            date=formatted_date,
            batch_no=batch.batch_code,
            mfg_date=formatted_date,
            product_name=product.name,
            quantity=batch.output_quantity,
            unit=product.unit,
            parameters=parameters,
        )

        response = HttpResponse(stream, content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="COA_{batch.batch_code}.pdf"'
        return response
