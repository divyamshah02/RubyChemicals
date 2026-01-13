from rest_framework import viewsets, status
from rest_framework.response import Response
from .models import *
from .serializers import StockGroupSerializer, StockItemSerializer
from UserDetail.models import ActivityLog
from utils.decorators import handle_exceptions, check_authentication
from django.db import transaction
from django.db import transaction
from decimal import Decimal

class StockGroupViewSet(viewsets.ViewSet):

    @handle_exceptions
    @check_authentication(required_role='admin')
    def create(self, request):
        name = request.data.get("name")
        description = request.data.get("description", "")

        if not name:
            return Response({
                "success": False,
                "user_not_logged_in": False,
                "user_unauthorized": False,
                "data": None,
                "error": "Group name is required"
            }, status=400)

        group = StockGroup.objects.create(
            name=name,
            description=description
        )

        ActivityLog.objects.create(
            user=request.user,
            action="CREATE",
            model_name="StockGroup",
            record_id=str(group.id),
            description=f"Created stock group {group.name}"
        )

        return Response({
            "success": True,
            "user_not_logged_in": False,
            "user_unauthorized": False,
            "data": StockGroupSerializer(group).data,
            "error": None
        }, status=201)

    @handle_exceptions
    @check_authentication()
    def list(self, request):
        groups = StockGroup.objects.filter(is_active=True).order_by("name")
        data = StockGroupSerializer(groups, many=True).data

        return Response({
            "success": True,
            "user_not_logged_in": False,
            "user_unauthorized": False,
            "data": data,
            "error": None
        }, status=200)


class StockItemViewSet(viewsets.ViewSet):

    @handle_exceptions
    @check_authentication(required_role='admin')
    def create(self, request):
        serializer = StockItemSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({
                "success": False,
                "user_not_logged_in": False,
                "user_unauthorized": False,
                "data": None,
                "error": serializer.errors
            }, status=400)

        item = serializer.save()

        ActivityLog.objects.create(
            user=request.user,
            action="CREATE",
            model_name="StockItem",
            record_id=str(item.id),
            description=f"Created stock item {item.name}"
        )

        return Response({
            "success": True,
            "user_not_logged_in": False,
            "user_unauthorized": False,
            "data": StockItemSerializer(item).data,
            "error": None
        }, status=201)

    @handle_exceptions
    @check_authentication(required_role='admin')
    def update(self, request, pk=None):
        try:
            item = StockItem.objects.get(pk=pk)
        except StockItem.DoesNotExist:
            return Response({
                "success": False,
                "user_not_logged_in": False,
                "user_unauthorized": False,
                "data": None,
                "error": "Stock item not found"
            }, status=404)

        serializer = StockItemSerializer(item, data=request.data, partial=True)
        if not serializer.is_valid():
            return Response({
                "success": False,
                "user_not_logged_in": False,
                "user_unauthorized": False,
                "data": None,
                "error": serializer.errors
            }, status=400)

        item = serializer.save()

        ActivityLog.objects.create(
            user=request.user,
            action="UPDATE",
            model_name="StockItem",
            record_id=str(item.id),
            description=f"Updated stock item {item.name}"
        )

        return Response({
            "success": True,
            "user_not_logged_in": False,
            "user_unauthorized": False,
            "data": StockItemSerializer(item).data,
            "error": None
        }, status=200)

    @handle_exceptions
    @check_authentication()
    def list(self, request):
        items = StockItem.objects.filter(is_active=True).select_related("group")
        data = StockItemSerializer(items, many=True).data

        return Response({
            "success": True,
            "user_not_logged_in": False,
            "user_unauthorized": False,
            "data": data,
            "error": None
        }, status=200)

    @handle_exceptions
    @check_authentication()
    def retrieve(self, request, pk=None):
        try:
            item = StockItem.objects.get(pk=pk)
        except StockItem.DoesNotExist:
            return Response({
                "success": False,
                "user_not_logged_in": False,
                "user_unauthorized": False,
                "data": None,
                "error": "Stock item not found"
            }, status=404)

        inwards = item.inwards.all().values("date", "quantity", "notes")
        adjustments = item.adjustments.all().values("date", "adjustment_type", "quantity", "reason")
        consumptions = item.productionconsumption_set.all().values(
            "batch__batch_code", "quantity_used"
        )
        productions = item.production_batches.all().values(
            "batch_code", "output_quantity", "loss_quantity"
        )
        dispatches = item.dispatches.all().values("dispatch_date", "customer_name", "quantity")

        data = {
            "item": StockItemSerializer(item).data,
            "inwards": list(inwards),
            "adjustments": list(adjustments),
            "consumed_in_production": list(consumptions),
            "produced_batches": list(productions),
            "dispatches": list(dispatches)
        }

        return Response({
            "success": True,
            "user_not_logged_in": False,
            "user_unauthorized": False,
            "data": data,
            "error": None
        }, status=200)


class StockInwardViewSet(viewsets.ViewSet):

    @handle_exceptions
    @check_authentication()
    def create(self, request):
        stock_item_id = request.data.get("stock_item_id")
        quantity = request.data.get("quantity")
        date = request.data.get("date")
        notes = request.data.get("notes", "")

        if not stock_item_id or not quantity or not date:
            return Response({
                "success": False,
                "user_not_logged_in": False,
                "user_unauthorized": False,
                "data": None,
                "error": "stock_item_id, quantity and date are required"
            }, status=400)

        try:
            quantity = float(quantity)
            if quantity <= 0:
                raise ValueError
        except:
            return Response({
                "success": False,
                "user_not_logged_in": False,
                "user_unauthorized": False,
                "data": None,
                "error": "Quantity must be a positive number"
            }, status=400)

        try:
            item = StockItem.objects.select_for_update().get(id=stock_item_id)
        except StockItem.DoesNotExist:
            return Response({
                "success": False,
                "user_not_logged_in": False,
                "user_unauthorized": False,
                "data": None,
                "error": "Invalid stock item"
            }, status=404)

        with transaction.atomic():
            inward = StockInward.objects.create(
                date=date,
                stock_item=item,
                quantity=quantity,
                notes=notes,
                created_by=request.user
            )

            item.current_quantity += Decimal(quantity)
            item.save()

        ActivityLog.objects.create(
            user=request.user,
            action="STOCK_INWARD",
            model_name="StockItem",
            record_id=str(item.id),
            description=f"Inward {quantity} {item.unit} to {item.name}"
        )

        return Response({
            "success": True,
            "user_not_logged_in": False,
            "user_unauthorized": False,
            "data": {"stock_item": item.id, "new_quantity": item.current_quantity},
            "error": None
        }, status=201)


class StockAdjustmentViewSet(viewsets.ViewSet):

    @handle_exceptions
    @check_authentication()
    def create(self, request):
        stock_item_id = request.data.get("stock_item_id")
        quantity = request.data.get("quantity")
        adjustment_type = request.data.get("adjustment_type")
        reason = request.data.get("reason")
        date = request.data.get("date")

        if not all([stock_item_id, quantity, adjustment_type, reason, date]):
            return Response({
                "success": False,
                "user_not_logged_in": False,
                "user_unauthorized": False,
                "data": None,
                "error": "All fields are required"
            }, status=400)

        if adjustment_type not in ["increase", "decrease"]:
            return Response({
                "success": False,
                "user_not_logged_in": False,
                "user_unauthorized": False,
                "data": None,
                "error": "Invalid adjustment type"
            }, status=400)

        try:
            quantity = float(quantity)
            if quantity <= 0:
                raise ValueError
        except:
            return Response({
                "success": False,
                "user_not_logged_in": False,
                "user_unauthorized": False,
                "data": None,
                "error": "Quantity must be positive"
            }, status=400)

        try:
            item = StockItem.objects.select_for_update().get(id=stock_item_id)
        except StockItem.DoesNotExist:
            return Response({
                "success": False,
                "user_not_logged_in": False,
                "user_unauthorized": False,
                "data": None,
                "error": "Invalid stock item"
            }, status=404)

        with transaction.atomic():
            if adjustment_type == "decrease" and item.current_quantity < quantity:
                return Response({
                    "success": False,
                    "user_not_logged_in": False,
                    "user_unauthorized": False,
                    "data": None,
                    "error": "Insufficient stock for this adjustment"
                }, status=400)

            if adjustment_type == "increase":
                item.current_quantity += Decimal(quantity)
            else:
                item.current_quantity -= Decimal(quantity)

            item.save()

            StockAdjustment.objects.create(
                date=date,
                stock_item=item,
                adjustment_type=adjustment_type,
                quantity=quantity,
                reason=reason,
                created_by=request.user
            )

        ActivityLog.objects.create(
            user=request.user,
            action="STOCK_ADJUSTMENT",
            model_name="StockItem",
            record_id=str(item.id),
            description=f"{adjustment_type} {quantity} {item.unit} for {item.name} ({reason})"
        )

        return Response({
            "success": True,
            "user_not_logged_in": False,
            "user_unauthorized": False,
            "data": {"stock_item": item.id, "new_quantity": item.current_quantity},
            "error": None
        }, status=201)


class ProductionBatchViewSet(viewsets.ViewSet):

    @handle_exceptions
    @check_authentication()
    def list(self, request):
        batches = ProductionBatch.objects.all().order_by("-production_date", "-created_at")

        data = []

        for b in batches:
            data.append({
                "id": b.id,
                "batch_code": b.batch_code,
                "product_id": b.product.id,
                "product_name": b.product.name,
                "production_date": b.production_date,
                "output_quantity": b.output_quantity,
                "loss_quantity": b.loss_quantity,
                "created_by": b.created_by.name if b.created_by else None,
            })

        return Response({
            "success": True,
            "user_not_logged_in": False,
            "user_unauthorized": False,
            "data": data,
            "error": None
        }, status=200)

    @handle_exceptions
    @check_authentication()
    def create(self, request):
        data = request.data

        batch_code = data.get("batch_code")
        product_stock_item_id = data.get("product_stock_item_id")
        production_date = data.get("production_date")
        output_quantity = data.get("output_quantity")
        loss_quantity = data.get("loss_quantity", 0)
        consumptions = data.get("consumptions", [])

        if not all([batch_code, product_stock_item_id, production_date, output_quantity, consumptions]):
            return Response({
                "success": False,
                "user_not_logged_in": False,
                "user_unauthorized": False,
                "data": None,
                "error": "Missing required fields"
            }, status=400)

        try:
            output_quantity = float(output_quantity)
            loss_quantity = float(loss_quantity)
        except:
            return Response({
                "success": False,
                "user_not_logged_in": False,
                "user_unauthorized": False,
                "data": None,
                "error": "Invalid quantity"
            }, status=400)

        try:
            product_item = StockItem.objects.select_for_update().get(id=product_stock_item_id)
        except StockItem.DoesNotExist:
            return Response({
                "success": False,
                "user_not_logged_in": False,
                "user_unauthorized": False,
                "data": None,
                "error": "Invalid product stock item"
            }, status=404)

        with transaction.atomic():

            # Lock all consumed stock items
            stock_ids = [c["stock_item_id"] for c in consumptions]
            items = StockItem.objects.select_for_update().filter(id__in=stock_ids)

            item_map = {item.id: item for item in items}

            # Check stock availability
            for c in consumptions:
                item = item_map.get(int(c["stock_item_id"]))
                qty = float(c["quantity"])

                if not item:
                    raise Exception("Invalid stock item in consumption")

                if item.current_quantity < qty:
                    return Response({
                        "success": False,
                        "user_not_logged_in": False,
                        "user_unauthorized": False,
                        "data": None,
                        "error": f"Insufficient stock for {item.name}"
                    }, status=400)

            # Create batch
            batch = ProductionBatch.objects.create(
                batch_code=batch_code,
                product=product_item,
                production_date=production_date,
                output_quantity=output_quantity,
                loss_quantity=loss_quantity,
                created_by=request.user
            )

            # Consume raw + packing
            for c in consumptions:
                item = item_map[int(c["stock_item_id"])]
                qty = float(c["quantity"])

                ProductionConsumption.objects.create(
                    batch=batch,
                    stock_item=item,
                    quantity_used=qty
                )

                item.current_quantity -= Decimal(qty)
                item.save()

            # Increase finished goods
            product_item.current_quantity += Decimal(output_quantity)
            product_item.save()

        ActivityLog.objects.create(
            user=request.user,
            action="PRODUCTION",
            model_name="ProductionBatch",
            record_id=batch.batch_code,
            description=f"Produced {output_quantity} {product_item.unit} of {product_item.name}"
        )

        return Response({
            "success": True,
            "user_not_logged_in": False,
            "user_unauthorized": False,
            "data": {"batch": batch.batch_code},
            "error": None
        }, status=201)


class DispatchViewSet(viewsets.ViewSet):

    @handle_exceptions
    @check_authentication()
    def list(self, request):
        dispatches = Dispatch.objects.select_related("stock_item").order_by("-dispatch_date", "-created_at")

        data = []

        for d in dispatches:
            data.append({
                "id": d.id,
                "dispatch_date": d.dispatch_date,
                "customer_name": d.customer_name,
                "stock_item_id": d.stock_item.id,
                "stock_item_name": d.stock_item.name,
                "quantity": d.quantity,
                "created_by": d.created_by.name if d.created_by else None,
            })

        return Response({
            "success": True,
            "user_not_logged_in": False,
            "user_unauthorized": False,
            "data": data,
            "error": None
        }, status=200)

    @handle_exceptions
    @check_authentication()
    def create(self, request):
        stock_item_id = request.data.get("stock_item_id")
        quantity = request.data.get("quantity")
        customer_name = request.data.get("customer_name")
        dispatch_date = request.data.get("dispatch_date")
        notes = request.data.get("notes", "")

        if not all([stock_item_id, quantity, customer_name, dispatch_date]):
            return Response({
                "success": False,
                "user_not_logged_in": False,
                "user_unauthorized": False,
                "data": None,
                "error": "All fields are required"
            }, status=400)

        try:
            quantity = float(quantity)
            if quantity <= 0:
                raise ValueError
        except:
            return Response({
                "success": False,
                "user_not_logged_in": False,
                "user_unauthorized": False,
                "data": None,
                "error": "Invalid quantity"
            }, status=400)

        try:
            item = StockItem.objects.select_for_update().get(id=stock_item_id)
        except StockItem.DoesNotExist:
            return Response({
                "success": False,
                "user_not_logged_in": False,
                "user_unauthorized": False,
                "data": None,
                "error": "Invalid stock item"
            }, status=404)

        with transaction.atomic():
            if item.current_quantity < quantity:
                return Response({
                    "success": False,
                    "user_not_logged_in": False,
                    "user_unauthorized": False,
                    "data": None,
                    "error": "Insufficient stock for dispatch"
                }, status=400)

            item.current_quantity -= Decimal(quantity)
            item.save()

            Dispatch.objects.create(
                dispatch_date=dispatch_date,
                customer_name=customer_name,
                stock_item=item,
                quantity=quantity,
                notes=notes,
                created_by=request.user
            )

        ActivityLog.objects.create(
            user=request.user,
            action="DISPATCH",
            model_name="StockItem",
            record_id=str(item.id),
            description=f"Dispatched {quantity} {item.unit} of {item.name} to {customer_name}"
        )

        return Response({
            "success": True,
            "user_not_logged_in": False,
            "user_unauthorized": False,
            "data": {"stock_item": item.id, "new_quantity": item.current_quantity},
            "error": None
        }, status=201)


class ExpenseHeadViewSet(viewsets.ViewSet):

    @handle_exceptions
    @check_authentication(required_role='admin')
    def create(self, request):
        name = request.data.get("name")

        if not name:
            return Response({
                "success": False,
                "user_not_logged_in": False,
                "user_unauthorized": False,
                "data": None,
                "error": "Expense head name is required"
            }, status=400)

        head = ExpenseHead.objects.create(name=name)

        ActivityLog.objects.create(
            user=request.user,
            action="CREATE",
            model_name="ExpenseHead",
            record_id=str(head.id),
            description=f"Created expense head {head.name}"
        )

        return Response({
            "success": True,
            "user_not_logged_in": False,
            "user_unauthorized": False,
            "data": {"id": head.id, "name": head.name},
            "error": None
        }, status=201)

    @handle_exceptions
    @check_authentication()
    def list(self, request):
        heads = ExpenseHead.objects.filter(is_active=True).order_by("name")
        data = [{"id": h.id, "name": h.name} for h in heads]

        return Response({
            "success": True,
            "user_not_logged_in": False,
            "user_unauthorized": False,
            "data": data,
            "error": None
        }, status=200)


class PettyCashViewSet(viewsets.ViewSet):

    @handle_exceptions
    @check_authentication()
    def list(self, request):
        expenses = PettyCash.objects.select_related("expense_head").order_by("-expense_date", "-created_at")

        data = []

        for e in expenses:
            data.append({
                "id": e.id,
                "expense_date": e.expense_date,
                "expense_head_id": e.expense_head.id,
                "expense_head_name": e.expense_head.name,
                "amount": e.amount,
                "notes": e.notes,
                "created_by": e.created_by.name if e.created_by else None
            })

        return Response({
            "success": True,
            "user_not_logged_in": False,
            "user_unauthorized": False,
            "data": data,
            "error": None
        }, status=200)

    @handle_exceptions
    @check_authentication()
    def create(self, request):
        expense_head_id = request.data.get("expense_head_id")
        amount = request.data.get("amount")
        expense_date = request.data.get("expense_date")
        notes = request.data.get("notes", "")

        if not all([expense_head_id, amount, expense_date]):
            return Response({
                "success": False,
                "user_not_logged_in": False,
                "user_unauthorized": False,
                "data": None,
                "error": "All fields are required"
            }, status=400)

        try:
            amount = float(amount)
            if amount <= 0:
                raise ValueError
        except:
            return Response({
                "success": False,
                "user_not_logged_in": False,
                "user_unauthorized": False,
                "data": None,
                "error": "Invalid amount"
            }, status=400)

        try:
            head = ExpenseHead.objects.get(id=expense_head_id)
        except ExpenseHead.DoesNotExist:
            return Response({
                "success": False,
                "user_not_logged_in": False,
                "user_unauthorized": False,
                "data": None,
                "error": "Invalid expense head"
            }, status=404)

        entry = PettyCash.objects.create(
            expense_date=expense_date,
            expense_head=head,
            amount=amount,
            notes=notes,
            created_by=request.user
        )

        ActivityLog.objects.create(
            user=request.user,
            action="PETTY_CASH",
            model_name="PettyCash",
            record_id=str(entry.id),
            description=f"{head.name} expense ₹{amount}"
        )

        return Response({
            "success": True,
            "user_not_logged_in": False,
            "user_unauthorized": False,
            "data": {"id": entry.id},
            "error": None
        }, status=201)
