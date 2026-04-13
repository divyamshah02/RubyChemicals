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
        """Admin dashboard - shows all data with accounting status"""
        
        # Stock items with low/negative quantities only
        low_stock_items = StockItem.objects.filter(
            current_quantity__lte=0
        ).values('id', 'name', 'group__name', 'current_quantity', 'unit').order_by('current_quantity')
        
        # Total stock items
        total_items = StockItem.objects.count()
        
        # Total stock groups
        total_groups = StockGroup.objects.count()
        
        # Production cards - unaccounted with batch and consumption counts
        unaccounted_cards_list = []
        for card in ProductionCard.objects.filter(accounted=False).values('id', 'production_code', 'production_date', 'total_output_quantity', 'unit', 'accounted'):
            batch_count = ProductionBatch.objects.filter(production_card_id=card['id']).count()
            consumption_count = ProductionConsumption.objects.filter(production_card_id=card['id']).count()
            card['batch_count'] = batch_count
            card['consumption_count'] = consumption_count
            unaccounted_cards_list.append(card)
        
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
            "recent_batches": list(recent_batches),
            "stock_groups": list(stock_groups),
            "negative_stock_count": StockItem.objects.filter(current_quantity__lt=0).count(),
            "unaccounted_count": ProductionCard.objects.filter(accounted=False).count(),
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
        """Accounts dashboard - shows critical stock and pending accounting"""
        
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
            card['consumption_count'] = consumption_count
            pending_cards.append(card)
        
        data = {
            "critical_stock_count": critical_stock.count(),
            "critical_stock_items": list(critical_stock),
            "pending_accounting_cards": pending_cards,
            "accounted_count": ProductionCard.objects.filter(accounted=True).count(),
        }
        
        return Response({
            "success": True,
            "user_not_logged_in": False,
            "user_unauthorized": False,
            "data": data,
            "error": None
        }, status=200)


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
