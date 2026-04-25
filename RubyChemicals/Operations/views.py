from rest_framework import viewsets, status
from rest_framework.response import Response
from django.http import HttpResponse
from .models import *
from .serializers import StockGroupSerializer, StockItemSerializer
from UserDetail.models import ActivityLog
from utils.decorators import handle_exceptions, check_authentication
from django.db import transaction
from decimal import Decimal
from datetime import datetime
from utils.create_product_card_pdf import generate_production_card

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

        # Update stock log for the inward date
        date = datetime.now().strftime("%Y-%m-%d")
        stock_log, _ = StockLog.objects.get_or_create(date=date)
        stock_data = stock_log.stock_data or {}
        stock_data[str(item.id)] = {
            "name": item.name,
            "qty": float(item.current_quantity),
            "unit": item.unit
        }
        stock_log.stock_data = stock_data
        stock_log.save()


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
    @check_authentication(required_role='admin')
    def partial_update(self, request, pk=None):
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

        # Update stock log for the inward date
        date = datetime.now().strftime("%Y-%m-%d")
        stock_log, _ = StockLog.objects.get_or_create(date=date)
        stock_data = stock_log.stock_data or {}
        stock_data[str(item.id)] = {
            "name": item.name,
            "qty": float(item.current_quantity),
            "unit": item.unit
        }
        stock_log.stock_data = stock_data
        stock_log.save()

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
        data = StockItemSerializer(items, many=True).data[::-1]

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
        # consumptions = item.productionconsumption_set.all().values(
        #     "batch__batch_code", "quantity_used"
        # )
        # productions = item.production_batches.all().values(
        #     "batch_code", "output_quantity", "loss_quantity"
        # )

        data = {
            "item": StockItemSerializer(item).data,
            "inwards": list(inwards),
            "adjustments": list(adjustments),
            # "consumed_in_production": list(consumptions),
            # "produced_batches": list(productions)
        }

        return Response({
            "success": True,
            "user_not_logged_in": False,
            "user_unauthorized": False,
            "data": data,
            "error": None
        }, status=200)

    @handle_exceptions
    @check_authentication()
    def destroy(self, request, pk=None):
        try:
            stock_item = StockItem.objects.get(id=pk, is_active=True)
        except StockItem.DoesNotExist:
            return Response({
                "success": False,
                "user_not_logged_in": False,
                "user_unauthorized": False,
                "data": None,
                "error": "Production card not found"
            }, status=404)

        # Soft delete production card and all related data
        with transaction.atomic():
            stock_item.is_active = False
            stock_item.save()            

        ActivityLog.objects.create(
            user=request.user,
            action="STOCK_ITEM_DELETE",
            model_name="StockItem",
            record_id=stock_item.name,
            description=f"Deleted stock item {stock_item.name} - {stock_item.group}"
        )

        return Response({
            "success": True,
            "user_not_logged_in": False,
            "user_unauthorized": False,
            "data": {"stock_item": stock_item.name},
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

            # Update stock log for the inward date
            stock_log, _ = StockLog.objects.get_or_create(date=date)
            stock_data = stock_log.stock_data or {}
            stock_data[str(item.id)] = {
                "name": item.name,
                "qty": float(item.current_quantity),
                "unit": item.unit
            }
            stock_log.stock_data = stock_data
            stock_log.save()

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

            # Update stock log for the adjustment date
            stock_log, _ = StockLog.objects.get_or_create(date=date)
            stock_data = stock_log.stock_data or {}
            stock_data[str(item.id)] = {
                "name": item.name,
                "qty": float(item.current_quantity),
                "unit": item.unit
            }
            stock_log.stock_data = stock_data
            stock_log.save()

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


class StockLogViewSet(viewsets.ViewSet):

    @handle_exceptions
    @check_authentication()
    def list(self, request):
        """Get all dates available for stock history"""
        logs = StockLog.objects.all().order_by('-date').values('date')
        return Response({
            "success": True,
            "user_not_logged_in": False,
            "user_unauthorized": False,
            "data": list(logs),
            "error": None
        }, status=200)

    @handle_exceptions
    @check_authentication()
    def retrieve(self, request, pk=None):
        """Get stock data for a specific date (pk = date in YYYY-MM-DD format)"""
        try:
            log = StockLog.objects.get(date=pk)
        except StockLog.DoesNotExist:
            return Response({
                "success": False,
                "user_not_logged_in": False,
                "user_unauthorized": False,
                "data": None,
                "error": "No stock data for this date"
            }, status=404)

        # Format data as table rows
        stock_items = []
        for stock_id, item_data in log.stock_data.items():
            stock_items.append({
                "id": stock_id,
                "name": item_data.get('name'),
                "quantity": item_data.get('qty'),
                "unit": item_data.get('unit')
            })

        return Response({
            "success": True,
            "user_not_logged_in": False,
            "user_unauthorized": False,
            "data": {
                "date": str(log.date),
                "items": stock_items
            },
            "error": None
        }, status=200)


class TodayStockLogViewSet(viewsets.ViewSet):
    """
    Generate or update today's latest stock log
    """

    @handle_exceptions
    @check_authentication()
    def list(self, request):
        """Get or generate today's stock log with all current stock items"""
        from datetime import date
        
        today = date.today()
        stock_log, _ = StockLog.objects.get_or_create(date=today)
        
        # Always update with current stock data
        stock_data = {}
        items = StockItem.objects.filter(is_active=True)
        
        for item in items:
            stock_data[str(item.id)] = {
                "name": item.name,
                "qty": float(item.current_quantity),
                "unit": item.unit,
                "group": item.group.name
            }
        
        stock_log.stock_data = stock_data
        stock_log.save()
        
        return Response({
            "success": True,
            "user_not_logged_in": False,
            "user_unauthorized": False,
            "data": None,
            "error": None
        }, status=200)


class ProductionCardViewSet(viewsets.ViewSet):

    @handle_exceptions
    @check_authentication()
    def list(self, request):
        cards = ProductionCard.objects.filter(is_active=True).prefetch_related('batches').order_by("-production_date", "-created_at")
        data = []
        for card in cards:
            data.append({
                "id": card.id,
                "production_code": card.production_code,
                "production_date": card.production_date,
                "product_name": card.product_name,
                "total_output_quantity": card.total_output_quantity,
                "total_loss": card.total_loss,
                "unit": card.unit,
                "batch_count": card.batches.filter(is_active=True).count(),
                "created_by": card.created_by.name if card.created_by else None,
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
    def retrieve(self, request, pk=None):
        try:
            card = ProductionCard.objects.prefetch_related('batches', 'consumptions__stock_item').get(pk=pk, is_active=True)
        except ProductionCard.DoesNotExist:
            return Response({
                "success": False,
                "user_not_logged_in": False,
                "user_unauthorized": False,
                "data": None,
                "error": "Production card not found"
            }, status=404)

        batches = []
        for batch in card.batches.filter(is_active=True):
            batches.append({
                "id": batch.id,
                "batch_code": batch.batch_code,
                "product_id": batch.product.id,
                "product_name": batch.product.name,
                "product_unit": batch.product.unit,
                "output_quantity": batch.output_quantity,
                "loss_quantity": batch.loss_quantity,
            })

        consumptions = []
        for consumption in card.consumptions.filter(is_active=True):
            consumptions.append({
                "id": consumption.id,
                "stock_item_id": consumption.stock_item.id,
                "stock_item_name": consumption.stock_item.name,
                "stock_item_unit": consumption.stock_item.unit,
                "quantity_used": consumption.quantity_used,
            })

        data = {
            "production_card": {
                "id": card.id,
                "production_code": card.production_code,
                "production_date": card.production_date,
                "product_name": card.product_name,
                "total_output_quantity": card.total_output_quantity,
                "total_loss": card.total_loss,
                "unit": card.unit,
                "remarks": card.remarks,
                "notes": card.notes,
                "created_by": card.created_by.name if card.created_by else None,
            },
            "batches": batches,
            "consumptions": consumptions,
        }

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
        production_code = data.get("production_code")
        production_date = data.get("production_date")
        product_name = data.get("product_name", "")
        total_output_quantity = data.get("total_output_quantity")
        total_loss = data.get("total_loss", 0)
        unit = data.get("unit", "kg")
        remarks = data.get("remarks", "")
        consumptions = data.get("consumptions", [])
        batches = data.get("batches", [])

        if not all([production_code, production_date, total_output_quantity, consumptions, batches]):
            return Response({
                "success": False,
                "user_not_logged_in": False,
                "user_unauthorized": False,
                "data": None,
                "error": "Missing required fields - need production code, date, output qty, consumptions, and batches"
            }, status=400)

        try:
            total_output_quantity = float(total_output_quantity)
            total_loss = float(total_loss) if total_loss else 0
        except:
            return Response({
                "success": False,
                "user_not_logged_in": False,
                "user_unauthorized": False,
                "data": None,
                "error": "Invalid quantity"
            }, status=400)

        with transaction.atomic():
            # Get all stock items needed
            raw_stock_ids = [c["stock_item_id"] for c in consumptions]
            batch_product_ids = [b["product_stock_item_id"] for b in batches]
            all_stock_ids = list(set(raw_stock_ids + batch_product_ids))
            
            items = StockItem.objects.select_for_update().filter(id__in=all_stock_ids)
            item_map = {item.id: item for item in items}

            # Check raw material stock availability
            for c in consumptions:
                item = item_map.get(int(c["stock_item_id"]))
                qty = float(c["quantity"])
                # if not item or item.current_quantity < qty:
                if not item:
                    return Response({
                        "success": False,
                        "user_not_logged_in": False,
                        "user_unauthorized": False,
                        "data": None,
                        "error": f"Insufficient stock for {item.name if item else 'material'}"
                    }, status=400)

            # Create production card with new fields
            card = ProductionCard.objects.create(
                production_code=production_code,
                production_date=production_date,
                product_name=product_name,
                total_output_quantity=total_output_quantity,
                total_loss=total_loss,
                unit=unit,
                remarks=remarks,
                created_by=request.user
            )

            # Create consumptions (raw materials deducted)
            for c in consumptions:
                item = item_map[int(c["stock_item_id"])]
                qty = float(c["quantity"])
                ProductionConsumption.objects.create(
                    production_card=card,
                    stock_item=item,
                    quantity_used=qty
                )
                item.current_quantity -= Decimal(qty)
                item.save()

            # Create batches and add finished goods to inventory
            for b in batches:
                product_item = item_map[int(b["product_stock_item_id"])]
                output_qty = float(b["output_quantity"])
                loss_qty = float(b.get("loss_quantity", 0))

                batch = ProductionBatch.objects.create(
                    batch_code=b["batch_code"],
                    production_card=card,
                    product=product_item,
                    output_quantity=output_qty,
                    loss_quantity=loss_qty,
                    created_by=request.user
                )

                product_item.current_quantity += Decimal(output_qty)
                product_item.save()

        ActivityLog.objects.create(
            user=request.user,
            action="PRODUCTION_CREATE",
            model_name="ProductionCard",
            record_id=card.production_code,
            description=f"Created production card {card.production_code} with {len(batches)} batches"
        )

        return Response({
            "success": True,
            "user_not_logged_in": False,
            "user_unauthorized": False,
            "data": {"production_card": card.production_code, "batches_created": len(batches)},
            "error": None
        }, status=201)

    @handle_exceptions
    @check_authentication()
    def update(self, request, pk=None):
        try:
            card = ProductionCard.objects.get(pk=pk, is_active=True)
        except ProductionCard.DoesNotExist:
            return Response({
                "success": False,
                "user_not_logged_in": False,
                "user_unauthorized": False,
                "data": None,
                "error": "Production card not found"
            }, status=404)

        data = request.data
        
        # Update parent card fields
        if "production_code" in data:
            card.production_code = data["production_code"]
        if "production_date" in data:
            card.production_date = data["production_date"]
        if "product_name" in data:
            card.product_name = data["product_name"]
        if "total_output_quantity" in data:
            try:
                card.total_output_quantity = float(data["total_output_quantity"])
            except:
                return Response({
                    "success": False,
                    "user_not_logged_in": False,
                    "user_unauthorized": False,
                    "data": None,
                    "error": "Invalid total output quantity"
                }, status=400)
        if "total_loss" in data:
            try:
                card.total_loss = float(data["total_loss"]) if data["total_loss"] else 0
            except:
                return Response({
                    "success": False,
                    "user_not_logged_in": False,
                    "user_unauthorized": False,
                    "data": None,
                    "error": "Invalid total loss"
                }, status=400)
        if "unit" in data:
            card.unit = data["unit"]
        if "remarks" in data:
            card.remarks = data["remarks"]
        if "notes" in data:
            card.notes = data["notes"]
            
        card.save()

        # Update consumptions if provided
        consumptions = data.get("consumptions", [])
        if consumptions:
            card.consumptions.filter(is_active=True).delete()
            for c in consumptions:
                try:
                    stock_item = StockItem.objects.get(id=c["stock_item_id"])
                    ProductionConsumption.objects.create(
                        production_card=card,
                        stock_item=stock_item,
                        quantity_used=float(c["quantity"])
                    )
                except StockItem.DoesNotExist:
                    return Response({
                        "success": False,
                        "user_not_logged_in": False,
                        "user_unauthorized": False,
                        "data": None,
                        "error": f"Stock item not found"
                    }, status=400)

        # Update batches if provided
        batches = data.get("batches", [])
        if batches:
            card.batches.filter(is_active=True).delete()
            for b in batches:
                try:
                    product_item = StockItem.objects.get(id=b["product_stock_item_id"])
                    ProductionBatch.objects.create(
                        batch_code=b["batch_code"],
                        production_card=card,
                        product=product_item,
                        output_quantity=float(b["output_quantity"]),
                        loss_quantity=float(b.get("loss_quantity", 0)),
                        created_by=request.user
                    )
                except StockItem.DoesNotExist:
                    return Response({
                        "success": False,
                        "user_not_logged_in": False,
                        "user_unauthorized": False,
                        "data": None,
                        "error": f"Product stock item not found"
                    }, status=400)

        ActivityLog.objects.create(
            user=request.user,
            action="PRODUCTION_UPDATE",
            model_name="ProductionCard",
            record_id=card.production_code,
            description=f"Updated production card {card.production_code}"
        )

        return Response({
            "success": True,
            "user_not_logged_in": False,
            "user_unauthorized": False,
            "data": {"production_card": card.production_code},
            "error": None
        }, status=200)

    @handle_exceptions
    @check_authentication()
    def destroy(self, request, pk=None):
        try:
            card = ProductionCard.objects.get(pk=pk, is_active=True)
        except ProductionCard.DoesNotExist:
            return Response({
                "success": False,
                "user_not_logged_in": False,
                "user_unauthorized": False,
                "data": None,
                "error": "Production card not found"
            }, status=404)

        # Soft delete production card and all related data
        with transaction.atomic():
            card.is_active = False
            card.save()

            # Soft delete all batches
            card.batches.all().update(is_active=False)

            # Soft delete all consumptions
            card.consumptions.all().update(is_active=False)

        ActivityLog.objects.create(
            user=request.user,
            action="PRODUCTION_DELETE",
            model_name="ProductionCard",
            record_id=card.production_code,
            description=f"Deleted production card {card.production_code}"
        )

        return Response({
            "success": True,
            "user_not_logged_in": False,
            "user_unauthorized": False,
            "data": {"production_card": card.production_code},
            "error": None
        }, status=200)


class DownloadProductionCardViewSet(viewsets.ViewSet):   

    # @handle_exceptions
    @check_authentication()
    def retrieve(self, request, pk=None):
        try:
            card = ProductionCard.objects.prefetch_related('batches', 'consumptions__stock_item').get(pk=pk, is_active=True)
        except ProductionCard.DoesNotExist:
            return Response({
                "success": False,
                "user_not_logged_in": False,
                "user_unauthorized": False,
                "data": None,
                "error": "Production card not found"
            }, status=404)

        batches = []
        for batch in card.batches.filter(is_active=True):
            batches.append({
                "id": batch.id,
                "batch_code": batch.batch_code,
                "product_id": batch.product.id,
                "product_name": batch.product.name,
                "product_unit": batch.product.unit,
                "output_quantity": batch.output_quantity,
                "loss_quantity": batch.loss_quantity,
            })

        consumptions = []
        for consumption in card.consumptions.filter(is_active=True):
            consumptions.append({
                "id": consumption.id,
                "stock_item_id": consumption.stock_item.id,
                "stock_item_name": consumption.stock_item.name,
                "stock_item_unit": consumption.stock_item.unit,
                "quantity_used": consumption.quantity_used,
            })

        data = {
            "product_name": card.product_name,
            "code": card.production_code,
            "date": card.production_date,            
            "total_output": card.total_output_quantity,
            "uom": card.unit,
            "total_loss": card.total_loss,
            "remarks": card.remarks,
            "batches": batches,
            "raw_materials": consumptions,
            "production_incharge": "Divyam Shah",
            "approved_by": "Divyam Shah",
            "accounted_by": "Divyam Shah"
        }

        output_stream = generate_production_card(
            input_pdf_path=r"production_card_template.pdf",
            output_pdf_path="production_card_output_challan.pdf",
            product_name=str(data['product_name']),
            code=str(data['code']),
            date=str(data['date']),
            total_output=str(data['total_output']),
            uom=str(data['uom']),
            total_loss=str(data['total_loss']),
            remarks=str(data['remarks']),
            batches=data['batches'],
            raw_materials=data['raw_materials'],
            production_incharge=str(data['production_incharge']),
            approved_by=str(data['approved_by']),
            accounted_by=str(data['accounted_by'])
        )
        
        response = HttpResponse(
            output_stream,
            content_type='application/pdf'
        )
        response['Content-Disposition'] = 'attachment; filename="generated.pdf"'

        return response

        return Response({
            "success": True,
            "user_not_logged_in": False,
            "user_unauthorized": False,
            "data": data,
            "error": None
        }, status=200)


class ProductionBatchViewSet(viewsets.ViewSet):

    @handle_exceptions
    @check_authentication()
    def list(self, request):
        batches = ProductionBatch.objects.select_related('product', 'production_card').order_by("-created_at")
        data = []
        for b in batches:
            data.append({
                "id": b.id,
                "batch_code": b.batch_code,
                "production_card_id": b.production_card.id,
                "production_code": b.production_card.production_code,
                "production_date": b.production_card.production_date,
                "product_id": b.product.id,
                "product_name": b.product.name,
                "product_unit": b.product.unit,
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
        production_card_id = data.get("production_card_id")
        product_stock_item_id = data.get("product_stock_item_id")
        output_quantity = data.get("output_quantity")
        loss_quantity = data.get("loss_quantity", 0)

        if not all([batch_code, production_card_id, product_stock_item_id, output_quantity]):
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
            card = ProductionCard.objects.get(id=production_card_id)
            product_item = StockItem.objects.select_for_update().get(id=product_stock_item_id)
        except (ProductionCard.DoesNotExist, StockItem.DoesNotExist):
            return Response({
                "success": False,
                "user_not_logged_in": False,
                "user_unauthorized": False,
                "data": None,
                "error": "Invalid production card or product"
            }, status=404)

        with transaction.atomic():
            batch = ProductionBatch.objects.create(
                batch_code=batch_code,
                production_card=card,
                product=product_item,
                output_quantity=output_quantity,
                loss_quantity=loss_quantity,
                created_by=request.user
            )

            product_item.current_quantity += Decimal(output_quantity)
            product_item.save()

            card.total_output_quantity += Decimal(output_quantity)
            card.save()

        ActivityLog.objects.create(
            user=request.user,
            action="BATCH_CREATE",
            model_name="ProductionBatch",
            record_id=batch.batch_code,
            description=f"Created batch {batch.batch_code} in {card.production_code}"
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
        """List all dispatches with related data"""        
        dispatches = Dispatch.objects.filter(is_active=True).select_related('client', 'shipping_address').prefetch_related('items').order_by('-dispatch_date') 
        
        data = []
        for dispatch in dispatches:
            items = []
            total_quantity = 0
            for item in dispatch.items.all():
                items.append({
                    "id": item.id,
                    "stock_item_id": item.stock_item.id,
                    "stock_item_name": item.stock_item.name,
                    "quantity": str(item.quantity),
                    "unit": item.unit
                })
                total_quantity += float(item.quantity)
            
            data.append({
                "id": dispatch.id,
                "dispatch_code": dispatch.dispatch_code,
                "accounted": dispatch.accounted,
                "dispatch_date": dispatch.dispatch_date,
                "client_name": dispatch.client.company_name if dispatch.client else None,
                "client": dispatch.client.id if dispatch.client else None,
                "client_phone": dispatch.client.phone if dispatch.client else None,
                "vehicle_type": dispatch.vehicle_type,
                "vehicle_number": dispatch.vehicle_number,
                "freight_amount": str(dispatch.freight_amount),
                "total_quantity": total_quantity,
                "items": items,
                "shipping_address": dispatch.shipping_address.street if dispatch.shipping_address else None,
                "shipping_address_full": f"{dispatch.shipping_address.street}, {dispatch.shipping_address.city}, {dispatch.shipping_address.state}" if dispatch.shipping_address else None,
                "shipping_address_id": dispatch.shipping_address.id if dispatch.shipping_address else None,
                "notes": dispatch.notes,
                "created_at": dispatch.created_at
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
    def retrieve(self, request, pk=None):
        """Get single dispatch with all its items"""
        try:
            dispatch = Dispatch.objects.select_related('client', 'shipping_address').prefetch_related('items').get(pk=pk)
        except Dispatch.DoesNotExist:
            return Response({
                "success": False,
                "user_not_logged_in": False,
                "user_unauthorized": False,
                "data": None,
                "error": "Dispatch not found"
            }, status=404)

        items = []
        for item in dispatch.items.all():
            items.append({
                "id": item.id,
                "stock_item_id": item.stock_item.id,
                "stock_item_name": item.stock_item.name,
                "quantity": str(item.quantity),
                "unit": item.unit
            })

        data = {
            "id": dispatch.id,
            "dispatch_code": dispatch.dispatch_code,
            "dispatch_date": dispatch.dispatch_date,
            "client_id": dispatch.client.id if dispatch.client else None,
            "client_name": dispatch.client.company_name if dispatch.client else None,
            "vehicle_type": dispatch.vehicle_type,
            "vehicle_number": dispatch.vehicle_number,
            "freight_amount": str(dispatch.freight_amount),
            "shipping_address_id": dispatch.shipping_address.id if dispatch.shipping_address else None,
            "items": items,
            "notes": dispatch.notes
        }

        return Response({
            "success": True,
            "user_not_logged_in": False,
            "user_unauthorized": False,
            "data": data,
            "error": None
        }, status=200)

    @handle_exceptions
    @check_authentication()
    @transaction.atomic
    def create(self, request):
        """Create new dispatch with multiple items"""
        dispatch_date = request.data.get("dispatch_date")
        vehicle_type = request.data.get("vehicle_type", "")
        vehicle_number = request.data.get("vehicle_number", "")
        freight_amount = request.data.get("freight_amount", 0)
        client_id = request.data.get("client")
        shipping_address_id = request.data.get("shipping_address")
        notes = request.data.get("notes", "")
        dispatch_items = request.data.get("items", [])  # List of items

        if not all([dispatch_date, dispatch_items]):
            return Response({
                "success": False,
                "user_not_logged_in": False,
                "user_unauthorized": False,
                "data": None,
                "error": "Missing required fields (dispatch_date, items)"
            }, status=400)

        if not isinstance(dispatch_items, list) or len(dispatch_items) == 0:
            return Response({
                "success": False,
                "user_not_logged_in": False,
                "user_unauthorized": False,
                "data": None,
                "error": "Items must be a non-empty list"
            }, status=400)

        try:
            # Create dispatch (code auto-generated)
            dispatch = Dispatch.objects.create(
                dispatch_date=dispatch_date,
                vehicle_type=vehicle_type,
                vehicle_number=vehicle_number,
                freight_amount=freight_amount,
                client_id=client_id if client_id else None,
                shipping_address_id=shipping_address_id if shipping_address_id else None,
                notes=notes,
                created_by=request.user
            )

            # Create dispatch items
            for item in dispatch_items:
                stock_item_id = item.get("stock_item_id")
                quantity = item.get("quantity")
                unit = item.get("unit", "kg")

                if not all([stock_item_id, quantity]):
                    return Response({
                        "success": False,
                        "user_not_logged_in": False,
                        "user_unauthorized": False,
                        "data": None,
                        "error": "Each item must have stock_item_id and quantity"
                    }, status=400)

                DispatchItem.objects.create(
                    dispatch=dispatch,
                    stock_item_id=stock_item_id,
                    quantity=quantity,
                    unit=unit
                )

            # Log activity
            ActivityLog.objects.create(
                user=request.user,
                action=f"Created Dispatch {dispatch.dispatch_code}"
            )

            return Response({
                "success": True,
                "user_not_logged_in": False,
                "user_unauthorized": False,
                "data": {"id": dispatch.id, "dispatch_code": dispatch.dispatch_code},
                "error": None
            }, status=201)

        except Exception as e:
            return Response({
                "success": False,
                "user_not_logged_in": False,
                "user_unauthorized": False,
                "data": None,
                "error": str(e)
            }, status=400)

    @handle_exceptions
    @check_authentication()
    @transaction.atomic
    def update(self, request, pk=None):
        """Update dispatch"""
        try:
            dispatch = Dispatch.objects.get(pk=pk)
        except Dispatch.DoesNotExist:
            return Response({
                "success": False,
                "user_not_logged_in": False,
                "user_unauthorized": False,
                "data": None,
                "error": "Dispatch not found"
            }, status=404)

        # Update basic fields
        dispatch.dispatch_date = request.data.get("dispatch_date", dispatch.dispatch_date)
        dispatch.vehicle_type = request.data.get("vehicle_type", dispatch.vehicle_type)
        dispatch.vehicle_number = request.data.get("vehicle_number", dispatch.vehicle_number)
        dispatch.freight_amount = request.data.get("freight_amount", dispatch.freight_amount)
        dispatch.notes = request.data.get("notes", dispatch.notes)

        if "client" in request.data:
            dispatch.client_id = request.data.get("client")
        if "shipping_address" in request.data:
            dispatch.shipping_address_id = request.data.get("shipping_address")

        dispatch.save()

        # Update items if provided
        if "items" in request.data:
            dispatch.items.all().delete()
            for item in request.data.get("items", []):
                DispatchItem.objects.create(
                    dispatch=dispatch,
                    stock_item_id=item.get("stock_item_id"),
                    quantity=item.get("quantity"),
                    unit=item.get("unit", "kg")
                )

        return Response({
            "success": True,
            "user_not_logged_in": False,
            "user_unauthorized": False,
            "data": {"id": dispatch.id, "dispatch_code": dispatch.dispatch_code},
            "error": None
        }, status=200)

    @handle_exceptions
    @check_authentication()
    def destroy(self, request, pk=None):
        """Delete dispatch"""
        try:
            dispatch = Dispatch.objects.get(pk=pk)
            dispatch_code = dispatch.dispatch_code
            dispatch.delete()
            
            ActivityLog.objects.create(
                user=request.user,
                action=f"Deleted Dispatch {dispatch_code}"
            )
            
            return Response({
                "success": True,
                "user_not_logged_in": False,
                "user_unauthorized": False,
                "data": None,
                "error": None
            }, status=200)
        except Dispatch.DoesNotExist:
            return Response({
                "success": False,
                "user_not_logged_in": False,
                "user_unauthorized": False,
                "data": None,
                "error": "Dispatch not found"
            }, status=404)


    @handle_exceptions
    @check_authentication()
    def destroy(self, request, pk=None):
        """Delete dispatch"""
        try:
            dispatch = Dispatch.objects.get(pk=pk)
            dispatch_code = dispatch.dispatch_code
            dispatch.delete()
            
            ActivityLog.objects.create(
                user=request.user,
                action=f"Deleted Dispatch {dispatch_code}"
            )
            
            return Response({
                "success": True,
                "user_not_logged_in": False,
                "user_unauthorized": False,
                "data": None,
                "error": None
            }, status=200)
        except Dispatch.DoesNotExist:
            return Response({
                "success": False,
                "user_not_logged_in": False,
                "user_unauthorized": False,
                "data": None,
                "error": "Dispatch not found"
            }, status=404)


    @handle_exceptions
    @check_authentication()
    @transaction.atomic
    def partial_update(self, request, pk=None):
        """Partial update dispatch (PATCH) - supports updating individual fields and items"""
        try:
            dispatch = Dispatch.objects.get(pk=pk)
        except Dispatch.DoesNotExist:
            return Response({
                "success": False,
                "user_not_logged_in": False,
                "user_unauthorized": False,
                "data": None,
                "error": "Dispatch not found"
            }, status=404)

        # Update individual fields if provided
        if "dispatch_date" in request.data:
            dispatch.dispatch_date = request.data.get("dispatch_date")
        if "vehicle_type" in request.data:
            dispatch.vehicle_type = request.data.get("vehicle_type")
        if "vehicle_number" in request.data:
            dispatch.vehicle_number = request.data.get("vehicle_number")
        if "freight_amount" in request.data:
            dispatch.freight_amount = request.data.get("freight_amount")
        if "accounted" in request.data:
            dispatch.accounted = request.data.get("accounted")
        if "client" in request.data:
            dispatch.client_id = request.data.get("client")
        if "shipping_address" in request.data:
            dispatch.shipping_address_id = request.data.get("shipping_address")
        if "notes" in request.data:
            dispatch.notes = request.data.get("notes")

        dispatch.save()

        # Update items if provided (add/update items)
        if "items" in request.data:
            dispatch.items.all().delete()
            for item in request.data.get("items", []):
                DispatchItem.objects.create(
                    dispatch=dispatch,
                    stock_item_id=item.get("stock_item_id"),
                    quantity=item.get("quantity"),
                    unit=item.get("unit", "kg")
                )

        ActivityLog.objects.create(
            user=request.user,
            action="UPDATE",
            model_name="Dispatch",
            record_id=dispatch.dispatch_code,
            description=f"Updated dispatch {dispatch.dispatch_code}"
        )

        return Response({
            "success": True,
            "user_not_logged_in": False,
            "user_unauthorized": False,
            "data": {"id": dispatch.id, "dispatch_code": dispatch.dispatch_code},
            "error": None
        }, status=200)

        return Response({
                "success": False,
                "user_not_logged_in": False,
                "user_unauthorized": False,
                "data": None,
                "error": "Dispatch not found"
            }, status=404)

        dispatch_code = request.data.get("dispatch_code", dispatch.dispatch_code)
        
        # Check if dispatch code is being changed to an existing code
        if dispatch_code != dispatch.dispatch_code and Dispatch.objects.filter(dispatch_code=dispatch_code).exists():
            return Response({
                "success": False,
                "user_not_logged_in": False,
                "user_unauthorized": False,
                "data": None,
                "error": "Dispatch code already exists"
            }, status=400)

        dispatch.dispatch_code = dispatch_code
        dispatch.dispatch_date = request.data.get("dispatch_date", dispatch.dispatch_date)
        if request.data.get("stock_item"):
            dispatch.stock_item_id = request.data.get("stock_item")
        dispatch.client_id = request.data.get("client", dispatch.client_id)
        dispatch.dispatch_quantity = request.data.get("dispatch_quantity", dispatch.dispatch_quantity)
        dispatch.unit = request.data.get("unit", dispatch.unit)
        dispatch.shipping_address_id = request.data.get("shipping_address", dispatch.shipping_address_id)
        dispatch.notes = request.data.get("notes", dispatch.notes)
        dispatch.save()

        ActivityLog.objects.create(
            user=request.user,
            action="UPDATE",
            model_name="Dispatch",
            record_id=dispatch_code,
            description=f"Updated dispatch {dispatch_code}"
        )

        return Response({
            "success": True,
            "user_not_logged_in": False,
            "user_unauthorized": False,
            "data": {"id": dispatch.id},
            "error": None
        }, status=200)

    @handle_exceptions
    @check_authentication()
    def destroy(self, request, pk=None):
        """Delete dispatch"""
        try:
            dispatch = Dispatch.objects.get(pk=pk)
            dispatch.is_active = False
            dispatch.save()
            return Response({
                "success": True,
                "user_not_logged_in": False,
                "user_unauthorized": False,
                "data": None,
                "error": None
            }, status=200)
        except Dispatch.DoesNotExist:
            return Response({
                "success": False,
                "user_not_logged_in": False,
                "user_unauthorized": False,
                "data": None,
                "error": "Dispatch not found"
            }, status=404)


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


class PettyCashAccountViewSet(viewsets.ViewSet):
    """Petty Cash Account management"""
    
    @handle_exceptions
    @check_authentication()
    def list(self, request):
        """List petty cash accounts with current balances"""
        accounts = PettyCashAccount.objects.all().values('id', 'cash_type', 'current_balance', 'credit_balance')
        return Response({
            "success": True,
            "user_not_logged_in": False,
            "user_unauthorized": False,
            "data": list(accounts),
            "error": None
        }, status=200)


class PettyCashViewSet(viewsets.ViewSet):
    """Petty Cash transactions (expenses and balance additions)"""
    
    @handle_exceptions
    @check_authentication()
    def list(self, request):
        """List all petty cash transactions for all accounts"""
        transactions = PettyCash.objects.select_related(
            'cash_account', 'expense_head', 'created_by'
        ).order_by('-expense_date')
        
        data = []
        for trans in transactions:
            data.append({
                'id': trans.id,
                'cash_type': trans.cash_account.cash_type,
                'expense_head_id': trans.expense_head_id if trans.expense_head else None,
                'expense_head_name': trans.expense_head.name if trans.expense_head else 'Balance Addition',
                'expense_date': str(trans.expense_date),
                'amount': str(trans.amount),
                'transaction_type': trans.transaction_type,
                'notes': trans.notes,
                'created_by': trans.created_by.username if trans.created_by else 'System',
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
        """Create petty cash transaction"""
        cash_type = request.data.get("cash_type")
        expense_head_id = request.data.get("expense_head_id")
        amount = request.data.get("amount")
        expense_date = request.data.get("expense_date")
        transaction_type = request.data.get("transaction_type")  # 'credit' or 'debit'
        notes = request.data.get("notes", "")
        
        if not all([cash_type, amount, expense_date, transaction_type]):
            return Response({
                "success": False,
                "user_not_logged_in": False,
                "user_unauthorized": False,
                "data": None,
                "error": "Missing required fields"
            }, status=400)
        
        try:
            # Get or create petty cash account
            account, created = PettyCashAccount.objects.get_or_create(cash_type=cash_type)
            
            # Get expense head if debit transaction
            expense_head = None
            if transaction_type == 'debit' and expense_head_id:
                expense_head = ExpenseHead.objects.get(id=expense_head_id)
            
            # Create transaction
            transaction = PettyCash.objects.create(
                cash_account=account,
                expense_head=expense_head,
                expense_date=expense_date,
                amount=amount,
                transaction_type=transaction_type,
                notes=notes,
                created_by=request.user
            )
            
            # Update account balance
            amount_decimal = Decimal(str(amount))
            if transaction_type == 'credit':
                account.current_balance += amount_decimal
                account.credit_balance += amount_decimal
            else:  # debit
                account.current_balance -= amount_decimal
            
            account.save()
            
            ActivityLog.objects.create(
                user=request.user,
                action="PETTY_CASH_TRANSACTION",
                model_name="PettyCash",
                record_id=f"{account.cash_type}",
                description=f"Petty Cash {account.get_cash_type_display()} - {transaction_type} ₹{amount}"
            )
            
            return Response({
                "success": True,
                "user_not_logged_in": False,
                "user_unauthorized": False,
                "data": {"id": transaction.id, "new_balance": str(account.current_balance)},
                "error": None
            }, status=201)
            
        except ExpenseHead.DoesNotExist:
            return Response({
                "success": False,
                "user_not_logged_in": False,
                "user_unauthorized": False,
                "data": None,
                "error": "Expense head not found"
            }, status=404)
        except Exception as e:
            return Response({
                "success": False,
                "user_not_logged_in": False,
                "user_unauthorized": False,
                "data": None,
                "error": str(e)
            }, status=400)


class ExpenseHeadViewSet(viewsets.ViewSet):
    """Expense Head management"""
    
    @handle_exceptions
    @check_authentication()
    def list(self, request):
        """List all active expense heads"""
        heads = ExpenseHead.objects.filter(is_active=True).values('id', 'name', 'is_active')
        return Response({
            "success": True,
            "user_not_logged_in": False,
            "user_unauthorized": False,
            "data": list(heads),
            "error": None
        }, status=200)
    
    @handle_exceptions
    @check_authentication()
    def create(self, request):
        """Create expense head"""
        name = request.data.get("name", "").strip()
        
        if not name:
            return Response({
                "success": False,
                "user_not_logged_in": False,
                "user_unauthorized": False,
                "data": None,
                "error": "Head name required"
            }, status=400)
        
        if ExpenseHead.objects.filter(name=name).exists():
            return Response({
                "success": False,
                "user_not_logged_in": False,
                "user_unauthorized": False,
                "data": None,
                "error": "Head already exists"
            }, status=400)
        
        head = ExpenseHead.objects.create(name=name, is_active=True)
        
        ActivityLog.objects.create(
            user=request.user,
            action="CREATE",
            model_name="ExpenseHead",
            record_id=head.name,
            description=f"Created expense head: {name}"
        )
        
        return Response({
            "success": True,
            "user_not_logged_in": False,
            "user_unauthorized": False,
            "data": {"id": head.id, "name": head.name},
            "error": None
        }, status=201)

