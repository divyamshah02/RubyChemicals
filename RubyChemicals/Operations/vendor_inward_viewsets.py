from rest_framework import viewsets, status
from rest_framework.response import Response
from .models import VendorInward, StockInward, StockItem
from .serializers import VendorInwardSerializer, VendorInwardItemSerializer
from UserDetail.models import ActivityLog
from utils.decorators import handle_exceptions, check_authentication
from django.db import transaction
from decimal import Decimal


class VendorInwardViewSet(viewsets.ViewSet):

    @handle_exceptions
    @check_authentication()
    def list(self, request):
        """List all vendor inward entries"""
        inwards = VendorInward.objects.filter(is_active=True).prefetch_related('items').order_by("-inward_date", "-created_at")
        data = []
        for inward in inwards:
            data.append({
                "id": inward.id,
                "inward_code": inward.inward_code,
                "inward_date": inward.inward_date,
                "vendor": inward.vendor.id,
                "vendor_name": inward.vendor.company_name,
                "accounted": inward.accounted,
                "notes": inward.notes,
                "item_count": inward.items.filter(is_active=True).count(),
                "created_by": inward.created_by.name if inward.created_by else None,
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
        """Get single vendor inward entry"""
        try:
            inward = VendorInward.objects.prefetch_related('items__stock_item').get(pk=pk, is_active=True)
        except VendorInward.DoesNotExist:
            return Response({
                "success": False,
                "user_not_logged_in": False,
                "user_unauthorized": False,
                "data": None,
                "error": "Vendor inward not found"
            }, status=404)

        items = []
        for item in inward.items.filter(is_active=True):
            items.append({
                "id": item.id,
                "stock_item": item.stock_item.id,
                "stock_item_name": item.stock_item.name,
                "quantity": item.quantity,
                "notes": item.notes,
                "date": item.date,
            })

        data = {
            "id": inward.id,
            "inward_code": inward.inward_code,
            "inward_date": inward.inward_date,
            "vendor": inward.vendor.id,
            "vendor_name": inward.vendor.company_name,
            "accounted": inward.accounted,
            "notes": inward.notes,
            "items": items,
            "created_by": inward.created_by.name if inward.created_by else None,
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
        """Create new vendor inward entry"""
        vendor_id = request.data.get("vendor")
        inward_date = request.data.get("inward_date")
        accounted = request.data.get("accounted", False)
        notes = request.data.get("notes", "")
        items_data = request.data.get("items", [])

        if not vendor_id or not inward_date or not items_data:
            return Response({
                "success": False,
                "user_not_logged_in": False,
                "user_unauthorized": False,
                "data": None,
                "error": "vendor, inward_date and items are required"
            }, status=400)

        try:
            from .models import VendorProfile
            vendor = VendorProfile.objects.get(id=vendor_id)
        except VendorProfile.DoesNotExist:
            return Response({
                "success": False,
                "user_not_logged_in": False,
                "user_unauthorized": False,
                "data": None,
                "error": "Vendor not found"
            }, status=404)

        with transaction.atomic():
            # Create vendor inward entry
            inward = VendorInward.objects.create(
                inward_date=inward_date,
                vendor=vendor,
                accounted=accounted,
                notes=notes,
                created_by=request.user
            )

            # Get all stock items needed
            stock_ids = [item["stock_item_id"] for item in items_data]
            items = StockItem.objects.select_for_update().filter(id__in=stock_ids)
            item_map = {item.id: item for item in items}

            # Create stock inward items and update quantities
            for item_data in items_data:
                stock_item_id = item_data.get("stock_item_id")
                quantity = item_data.get("quantity")
                item_notes = item_data.get("notes", "")

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
                    stock_item = item_map[stock_item_id]
                except KeyError:
                    return Response({
                        "success": False,
                        "user_not_logged_in": False,
                        "user_unauthorized": False,
                        "data": None,
                        "error": "Invalid stock item"
                    }, status=404)

                # Create stock inward record
                StockInward.objects.create(
                    inward_entry=inward,
                    date=inward_date,
                    stock_item=stock_item,
                    quantity=quantity,
                    notes=item_notes,
                    created_by=request.user
                )

                # Update stock item quantity
                stock_item.current_quantity += Decimal(quantity)
                stock_item.save()

                # Log activity
                ActivityLog.objects.create(
                    user=request.user,
                    action="STOCK_INWARD",
                    model_name="StockItem",
                    record_id=str(stock_item.id),
                    description=f"Inward {quantity} {stock_item.unit} to {stock_item.name} from {vendor.company_name}"
                )

        return Response({
            "success": True,
            "user_not_logged_in": False,
            "user_unauthorized": False,
            "data": {
                "id": inward.id,
                "inward_code": inward.inward_code,
                "vendor": vendor.id,
                "items_count": len(items_data)
            },
            "error": None
        }, status=201)

    @handle_exceptions
    @check_authentication()
    def destroy(self, request, pk=None):
        """Delete vendor inward entry"""
        try:
            inward = VendorInward.objects.get(id=pk)
            
            # Reverse the stock quantities
            for item in inward.items.filter(is_active=True):
                item.stock_item.current_quantity -= item.quantity
                item.stock_item.save()
                
                ActivityLog.objects.create(
                    user=request.user,
                    action="STOCK_INWARD_DELETED",
                    model_name="StockItem",
                    record_id=str(item.stock_item.id),
                    description=f"Deleted inward {item.quantity} {item.stock_item.unit} from {item.stock_item.name}"
                )
            
            inward.is_active = False
            inward.save()
            
            return Response({
                "success": True,
                "user_not_logged_in": False,
                "user_unauthorized": False,
                "data": None,
                "error": None
            }, status=200)
        except VendorInward.DoesNotExist:
            return Response({
                "success": False,
                "user_not_logged_in": False,
                "user_unauthorized": False,
                "data": None,
                "error": "Vendor inward not found"
            }, status=404)
