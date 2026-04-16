from rest_framework import viewsets, status
from rest_framework.response import Response
from .models import *
from .serializers import StockGroupSerializer, StockItemSerializer
from UserDetail.models import ActivityLog
from utils.decorators import handle_exceptions, check_authentication
from django.db import transaction
from django.db.models import F
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

        data = {
            "item": StockItemSerializer(item).data,
            "inwards": list(inwards),
            "adjustments": list(adjustments),
            "consumed_in_production": list(consumptions),
            "produced_batches": list(productions)
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


class ProductionCardViewSet(viewsets.ViewSet):
    """Production Card management"""
    
    @handle_exceptions
    @check_authentication()
    def list(self, request):
        """List all production cards"""
        cards = ProductionCard.objects.all().order_by('-production_date')
        data = []
        for card in cards:
            data.append({
                'id': card.id,
                'production_code': card.production_code,
                'production_date': str(card.production_date),
                'product_name': card.product_name,
                'total_output_quantity': str(card.total_output_quantity),
                'total_loss': str(card.total_loss),
                'unit': card.unit,
                'remarks': card.remarks,
                'accounted': card.accounted,
                'created_by': card.created_by.username if card.created_by else 'System',
                'created_at': str(card.created_at),
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
        """Retrieve single production card with batches and consumptions"""
        card = ProductionCard.objects.get(id=pk)
        batches = ProductionBatch.objects.filter(production_card=card).values(
            'id', 'batch_code', 'product_stock_item__name', 'output_quantity', 
            'loss_quantity', 'product_stock_item__unit'
        )
        consumptions = ProductionConsumption.objects.filter(production_card=card).values(
            'id', 'stock_item__name', 'quantity_used', 'stock_item__unit'
        )
        
        card_data = {
            'production_card': {
                'id': card.id,
                'production_code': card.production_code,
                'production_date': str(card.production_date),
                'product_name': card.product_name,
                'total_output_quantity': str(card.total_output_quantity),
                'total_loss': str(card.total_loss),
                'unit': card.unit,
                'remarks': card.remarks,
                'accounted': card.accounted,
            },
            'batches': list(batches.annotate(
                batch_code_val=F('batch_code'),
                product_name=F('product_stock_item__name'),
                product_unit=F('product_stock_item__unit')
            ).values('batch_code_val', 'product_name', 'output_quantity', 'loss_quantity', 'product_unit')),
            'consumptions': list(consumptions.annotate(
                stock_item_name=F('stock_item__name'),
                stock_item_unit=F('stock_item__unit')
            ).values('stock_item_name', 'quantity_used', 'stock_item_unit'))
        }
        
        return Response({
            "success": True,
            "user_not_logged_in": False,
            "user_unauthorized": False,
            "data": card_data,
            "error": None
        }, status=200)
    
    @handle_exceptions
    @check_authentication()
    def create(self, request):
        """Create production card with batches and consumptions"""
        production_code = request.data.get("production_code")
        production_date = request.data.get("production_date")
        product_name = request.data.get("product_name", "")
        total_output_quantity = request.data.get("total_output_quantity")
        total_loss = request.data.get("total_loss", 0)
        unit = request.data.get("unit", "kg")
        remarks = request.data.get("remarks", "")
        consumptions_data = request.data.get("consumptions", [])
        batches_data = request.data.get("batches", [])
        
        if not all([production_code, production_date, total_output_quantity]):
            return Response({
                "success": False,
                "user_not_logged_in": False,
                "user_unauthorized": False,
                "data": None,
                "error": "Missing required fields"
            }, status=400)
        
        try:
            # Create production card
            card = ProductionCard.objects.create(
                production_code=production_code,
                production_date=production_date,
                product_name=product_name,
                total_output_quantity=total_output_quantity,
                total_loss=Decimal(str(total_loss)),
                unit=unit,
                remarks=remarks,
                created_by=request.user
            )
            
            # Create consumptions
            for consumption in consumptions_data:
                stock_item = StockItem.objects.get(id=consumption['stock_item_id'])
                ProductionConsumption.objects.create(
                    production_card=card,
                    stock_item=stock_item,
                    quantity_used=consumption['quantity']
                )
                # Update stock quantity
                stock_item.current_quantity -= Decimal(str(consumption['quantity']))
                stock_item.save()
            
            # Create batches
            for batch in batches_data:
                product_stock_item = StockItem.objects.get(id=batch['product_stock_item_id'])
                ProductionBatch.objects.create(
                    batch_code=batch['batch_code'],
                    production_card=card,
                    product_stock_item=product_stock_item,
                    output_quantity=batch['output_quantity'],
                    loss_quantity=batch.get('loss_quantity', 0),
                    created_by=request.user
                )
                # Add to stock
                product_stock_item.current_quantity += Decimal(str(batch['output_quantity']))
                product_stock_item.save()
            
            ActivityLog.objects.create(
                user=request.user,
                action="CREATE",
                model_name="ProductionCard",
                record_id=production_code,
                description=f"Created production card: {production_code}"
            )
            
            return Response({
                "success": True,
                "user_not_logged_in": False,
                "user_unauthorized": False,
                "data": {"id": card.id, "production_code": production_code},
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
    def update(self, request, pk=None):
        """Update production card"""
        card = ProductionCard.objects.get(id=pk)
        
        # Update fields
        if 'product_name' in request.data:
            card.product_name = request.data.get('product_name')
        if 'total_loss' in request.data:
            card.total_loss = Decimal(str(request.data.get('total_loss')))
        if 'remarks' in request.data:
            card.remarks = request.data.get('remarks')
        
        card.save()
        
        ActivityLog.objects.create(
            user=request.user,
            action="UPDATE",
            model_name="ProductionCard",
            record_id=card.production_code,
            description=f"Updated production card: {card.production_code}"
        )
        
        return Response({
            "success": True,
            "user_not_logged_in": False,
            "user_unauthorized": False,
            "data": {"id": card.id},
            "error": None
        }, status=200)


class ProductionBatchViewSet(viewsets.ViewSet):
    """Production Batch listing"""
    
    @handle_exceptions
    @check_authentication()
    def list(self, request):
        """List all production batches"""
        batches = ProductionBatch.objects.select_related(
            'production_card', 'product_stock_item'
        ).order_by('-created_at')
        
        data = []
        for batch in batches:
            data.append({
                'id': batch.id,
                'batch_code': batch.batch_code,
                'production_card_id': batch.production_card_id,
                'production_code': batch.production_card.production_code if batch.production_card else 'N/A',
                'production_date': str(batch.production_card.production_date) if batch.production_card else 'N/A',
                'product_name': batch.product_stock_item.name,
                'product_unit': batch.product_stock_item.unit,
                'output_quantity': str(batch.output_quantity),
                'loss_quantity': str(batch.loss_quantity),
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

