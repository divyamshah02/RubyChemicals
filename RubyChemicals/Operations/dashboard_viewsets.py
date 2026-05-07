from rest_framework import viewsets
from rest_framework.response import Response
from .models import *
from utils.decorators import handle_exceptions, check_authentication
from django.db.models import Q
from decimal import Decimal
from UserDetail.models import ActivityLog

class AdminDashboardViewSet(viewsets.ViewSet):

    @handle_exceptions
    @check_authentication()
    def list(self, request):
        """Admin dashboard - shows all data with accounting status and latest dispatches"""
        
        # Stock items with low/negative quantities only
        low_stock_items = StockItem.objects.filter(
            current_quantity__lte=0, is_active=True
        ).values('id', 'name', 'group__name', 'current_quantity', 'unit').order_by('current_quantity')
        
        # Total stock items
        total_items = StockItem.objects.filter(is_active=True).count()
        
        # Total stock groups
        total_groups = StockGroup.objects.filter(is_active=True).count()
        
        # Production cards - unaccounted with batch and consumption counts (latest 5)
        unaccounted_cards_list = []
        for card in ProductionCard.objects.filter(accounted=False, is_active=True).select_related('product').order_by('-production_date').values('id', 'production_code', 'production_date', 'total_output_quantity', 'unit', 'accounted'):
            batch_count = ProductionBatch.objects.filter(production_card_id=card['id']).count()
            consumption_count = ProductionConsumption.objects.filter(production_card_id=card['id']).count()
            card['batch_count'] = batch_count
            card['consumption_count'] = consumption_count
            unaccounted_cards_list.append(card)
        
        # Latest dispatches (pending accounting, latest 5)
        pending_dispatches = []
        for dispatch in Dispatch.objects.filter(accounted=False, is_active=True).select_related('client').prefetch_related('items').order_by('-dispatch_date'):
            item_count = dispatch.items.count()
            total_qty = sum(float(item.quantity) for item in dispatch.items.all())
            pending_dispatches.append({
                'id': dispatch.id,
                'dispatch_code': dispatch.dispatch_code,
                'dispatch_date': str(dispatch.dispatch_date),
                'client_name': dispatch.client.company_name if dispatch.client else 'N/A',
                'vehicle_number': dispatch.vehicle_number,
                'freight_amount': str(dispatch.freight_amount),
                'item_count': item_count,
                'total_quantity': total_qty,
                'invoice_number': dispatch.invoice_number or 'N/A',
                'has_pdf': bool(dispatch.pdf),
            })
        
        # Pending inwards (unaccounted stock inwards, latest 5)
        pending_inwards = []
        for inward in VendorInward.objects.filter(accounted=False, is_active=True).select_related('vendor').prefetch_related('items').order_by('-inward_date'):
            item_count = inward.items.filter(is_active=True).count()
            pending_inwards.append({
                'id': inward.id,
                'inward_code': inward.inward_code,
                'inward_date': str(inward.inward_date),
                'vendor_name': inward.vendor.company_name,
                'item_count': item_count,
                'invoice_number': inward.invoice_number or 'N/A',
                'has_pdf': bool(inward.pdf),
            })
        
        # Recent batches
        recent_batches = ProductionBatch.objects.select_related(
            'product', 'production_card'
        ).order_by('-created_at')[:10].values(
            'batch_code', 'product__name', 'production_card__production_code', 
            'output_quantity', 'loss_quantity', 'created_at'
        )
        
        # Stock groups
        stock_groups = StockGroup.objects.values('id', 'name')
        
        data = {
            "low_stock_items": list(low_stock_items),
            "total_items": total_items,
            "total_groups": total_groups,
            "unaccounted_cards": unaccounted_cards_list,
            "pending_dispatches": pending_dispatches,
            "pending_inwards": pending_inwards,
            "recent_batches": list(recent_batches),
            "stock_groups": list(stock_groups),
            "negative_stock_count": StockItem.objects.filter(current_quantity__lt=0).count(),
            "unaccounted_count": ProductionCard.objects.filter(accounted=False).count(),
            "pending_inwards_count": VendorInward.objects.filter(accounted=False, is_active=True).count(),
        }
        
        return Response({
            "success": True,
            "user_not_logged_in": False,
            "user_unauthorized": False,
            "data": data,
            "error": None
        }, status=200)


class AdminMarkAccountedViewSet(viewsets.ViewSet):
    
    @handle_exceptions
    @check_authentication()
    def create(self, request):
        """Mark production card as accounted"""
        card_id = request.data.get("card_id")
        
        if not card_id:
            return Response({
                "success": False,
                "user_not_logged_in": False,
                "user_unauthorized": False,
                "data": None,
                "error": "Card ID required"
            }, status=400)
        
        try:
            card = ProductionCard.objects.get(id=card_id)
            card.accounted = True
            card.save()
            
            ActivityLog.objects.create(
                user=request.user,
                action="PRODUCTION_ACCOUNTED",
                model_name="ProductionCard",
                record_id=card.production_code,
                description=f"Production card {card.production_code} marked as accounted"
            )
            
            return Response({
                "success": True,
                "user_not_logged_in": False,
                "user_unauthorized": False,
                "data": {"card_id": card.id, "accounted": card.accounted},
                "error": None
            }, status=200)
        except ProductionCard.DoesNotExist:
            return Response({
                "success": False,
                "user_not_logged_in": False,
                "user_unauthorized": False,
                "data": None,
                "error": "Card not found"
            }, status=404)


class AccountsDashboardViewSet(viewsets.ViewSet):

    @handle_exceptions
    @check_authentication()
    def list(self, request):
        """Accounts dashboard - shows critical stock, pending accounting, and latest dispatches"""
        
        # Critical stock items (negative or zero quantity only)
        critical_stock = StockItem.objects.filter(
            current_quantity__lte=0
        ).values('id', 'name', 'group__name', 'current_quantity', 'unit').order_by('current_quantity')
        
        # Pending accounting cards with batch and consumption counts
        pending_cards = []
        for card in ProductionCard.objects.filter(accounted=False).values('id', 'production_code', 'production_date', 'total_output_quantity', 'unit'):
            batch_count = ProductionBatch.objects.filter(production_card_id=card['id']).count()
            consumption_count = ProductionConsumption.objects.filter(production_card_id=card['id']).count()
            card['batch_count'] = batch_count
            card['material_count'] = consumption_count
            pending_cards.append(card)
        
        # Pending dispatch accounting (latest 5)
        pending_dispatches = []
        for dispatch in Dispatch.objects.filter(accounted=False).select_related('client').prefetch_related('items').order_by('-dispatch_date')[:5]:
            item_count = dispatch.items.count()
            total_qty = sum(float(item.quantity) for item in dispatch.items.all())
            pending_dispatches.append({
                'id': dispatch.id,
                'dispatch_code': dispatch.dispatch_code,
                'dispatch_date': str(dispatch.dispatch_date),
                'client_name': dispatch.client.company_name if dispatch.client else 'N/A',
                'vehicle_number': dispatch.vehicle_number,
                'freight_amount': str(dispatch.freight_amount),
                'item_count': item_count,
                'total_quantity': total_qty,
            })
        
        data = {
            "critical_stock_count": critical_stock.count(),
            "critical_stock_items": list(critical_stock),
            "pending_accounting_cards": pending_cards,
            "pending_dispatches": pending_dispatches,
            "accounted_count": ProductionCard.objects.filter(accounted=True).count(),
            "unaccounted_count": ProductionCard.objects.filter(accounted=False).count(),
        }
        
        return Response({
            "success": True,
            "user_not_logged_in": False,
            "user_unauthorized": False,
            "data": data,
            "error": None
        }, status=200)


class AccountsMarkDispatchAccountedViewSet(viewsets.ViewSet):

    @handle_exceptions
    @check_authentication()
    def create(self, request):
        """Mark dispatch as accounted"""
        dispatch_id = request.data.get("dispatch_id")
        
        if not dispatch_id:
            return Response({
                "success": False,
                "user_not_logged_in": False,
                "user_unauthorized": False,
                "data": None,
                "error": "Dispatch ID required"
            }, status=400)
        
        try:
            dispatch = Dispatch.objects.get(id=dispatch_id)
            dispatch.accounted = True
            dispatch.save()
            
            ActivityLog.objects.create(
                user=request.user,
                action="DISPATCH_ACCOUNTED",
                model_name="Dispatch",
                record_id=dispatch.dispatch_code,
                description=f"Dispatch {dispatch.dispatch_code} marked as accounted"
            )
            
            return Response({
                "success": True,
                "user_not_logged_in": False,
                "user_unauthorized": False,
                "data": {"dispatch_id": dispatch.id, "accounted": dispatch.accounted},
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


class AdminMarkDispatchAccountedViewSet(viewsets.ViewSet):
    
    @handle_exceptions
    @check_authentication()
    def create(self, request):
        """Mark dispatch as accounted"""
        dispatch_id = request.data.get("dispatch_id")
        
        if not dispatch_id:
            return Response({
                "success": False,
                "user_not_logged_in": False,
                "user_unauthorized": False,
                "data": None,
                "error": "Dispatch ID required"
            }, status=400)
        
        try:
            dispatch = Dispatch.objects.get(id=dispatch_id)
            dispatch.accounted = True
            dispatch.save()
            
            ActivityLog.objects.create(
                user=request.user,
                action="DISPATCH_ACCOUNTED",
                model_name="Dispatch",
                record_id=dispatch.dispatch_code,
                description=f"Dispatch {dispatch.dispatch_code} marked as accounted"
            )
            
            return Response({
                "success": True,
                "user_not_logged_in": False,
                "user_unauthorized": False,
                "data": {"dispatch_id": dispatch.id, "accounted": dispatch.accounted},
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



class AccountsMarkAccountedViewSet(viewsets.ViewSet):

    @handle_exceptions
    @check_authentication()
    def create(self, request):
        """Mark production card as accounted"""
        card_id = request.data.get("card_id")
        
        if not card_id:
            return Response({
                "success": False,
                "user_not_logged_in": False,
                "user_unauthorized": False,
                "data": None,
                "error": "Card ID required"
            }, status=400)
        
        try:
            card = ProductionCard.objects.get(id=card_id)
            card.accounted = True
            card.save()
            
            ActivityLog.objects.create(
                user=request.user,
                action="PRODUCTION_ACCOUNTED",
                model_name="ProductionCard",
                record_id=card.production_code,
                description=f"Production card {card.production_code} marked as accounted"
            )
            
            return Response({
                "success": True,
                "user_not_logged_in": False,
                "user_unauthorized": False,
                "data": {"card_id": card.id, "accounted": card.accounted},
                "error": None
            }, status=200)
        except ProductionCard.DoesNotExist:
            return Response({
                "success": False,
                "user_not_logged_in": False,
                "user_unauthorized": False,
                "data": None,
                "error": "Card not found"
            }, status=404)


class ProductionDashboardViewSet(viewsets.ViewSet):

    @handle_exceptions
    @check_authentication()
    def list(self, request):
        """Production dashboard - shows stock items, production cards, batches, and groups"""
        
        # All stock items
        stock_items = StockItem.objects.values(
            'id', 'name', 'group__name', 'current_quantity', 'unit', 'rate'
        ).order_by('name')
        
        # Production cards with batch and consumption counts
        production_cards = []
        for card in ProductionCard.objects.values('id', 'production_code', 'production_date', 'total_output_quantity', 'unit', 'accounted'):
            batch_count = ProductionBatch.objects.filter(production_card_id=card['id']).count()
            consumption_count = ProductionConsumption.objects.filter(production_card_id=card['id']).count()
            card['batch_count'] = batch_count
            card['consumption_count'] = consumption_count
            production_cards.append(card)
        
        # Stock groups with item counts
        stock_groups = []
        for group in StockGroup.objects.values('id', 'name'):
            item_count = StockItem.objects.filter(group_id=group['id']).count()
            group['item_count'] = item_count
            stock_groups.append(group)
        
        data = {
            "total_items": StockItem.objects.count(),
            "total_productions": ProductionCard.objects.count(),
            "total_batches": ProductionBatch.objects.count(),
            "stock_items": list(stock_items),
            "production_cards": production_cards,
            "stock_groups": stock_groups,
            "low_stock_count": StockItem.objects.filter(current_quantity__lte=0).count(),
        }
        
        return Response({
            "success": True,
            "user_not_logged_in": False,
            "user_unauthorized": False,
            "data": data,
            "error": None
        }, status=200)
