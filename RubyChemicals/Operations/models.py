from django.db import models

# Create your models here.
class StockGroup(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class StockItem(models.Model):
    UNIT_CHOICES = [
        ('kg', 'Kilogram'),
        ('g', 'Gram'),
        ('pcs', 'Pieces'),
    ]

    name = models.CharField(max_length=255)
    group = models.ForeignKey(
        StockGroup,
        on_delete=models.PROTECT,
        related_name='items'
    )
    unit = models.CharField(max_length=10, choices=UNIT_CHOICES)

    current_quantity = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        default=0
    )

    rate = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True
    )

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('name', 'group')

    def __str__(self):
        return f"{self.name} ({self.group.name})"

class StockInward(models.Model):
    date = models.DateField()
    stock_item = models.ForeignKey(
        StockItem,
        on_delete=models.PROTECT,
        related_name='inwards'
    )
    quantity = models.DecimalField(max_digits=12, decimal_places=3)
    notes = models.TextField(blank=True)

    created_by = models.ForeignKey(
        'UserDetail.User',
        on_delete=models.SET_NULL,
        null=True
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Inward - {self.stock_item.name}"

class StockAdjustment(models.Model):
    ADJUSTMENT_TYPE = [
        ('increase', 'Increase'),
        ('decrease', 'Decrease'),
    ]

    date = models.DateField()
    stock_item = models.ForeignKey(
        StockItem,
        on_delete=models.PROTECT,
        related_name='adjustments'
    )
    adjustment_type = models.CharField(max_length=10, choices=ADJUSTMENT_TYPE)
    quantity = models.DecimalField(max_digits=12, decimal_places=3)
    reason = models.CharField(max_length=255)

    created_by = models.ForeignKey(
        'UserDetail.User',
        on_delete=models.SET_NULL,
        null=True
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Adjustment - {self.stock_item.name}"

class ProductionCard(models.Model):
    production_code = models.CharField(max_length=20, unique=True)
    production_date = models.DateField()
    
    total_output_quantity = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        default=0
    )
    
    unit = models.CharField(max_length=10, default='kg', choices=[
        ('kg', 'Kilogram'),
        ('g', 'Gram'),
        ('pcs', 'Pieces'),
    ])
    
    notes = models.TextField(blank=True)
    
    created_by = models.ForeignKey(
        'UserDetail.User',
        on_delete=models.SET_NULL,
        null=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.production_code


class ProductionBatch(models.Model):
    batch_code = models.CharField(max_length=20, unique=True)
    production_card = models.ForeignKey(
        ProductionCard,
        on_delete=models.CASCADE,
        related_name='batches',
        null=True,
        blank=True
    )
    
    product = models.ForeignKey(
        StockItem,
        on_delete=models.PROTECT,
        related_name='production_batches'
    )
    
    output_quantity = models.DecimalField(
        max_digits=12,
        decimal_places=3
    )
    loss_quantity = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        default=0
    )
    
    notes = models.TextField(blank=True)
    
    created_by = models.ForeignKey(
        'UserDetail.User',
        on_delete=models.SET_NULL,
        null=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.batch_code


class ProductionConsumption(models.Model):
    production_card = models.ForeignKey(
        ProductionCard,
        on_delete=models.CASCADE,
        related_name='consumptions',
        null=True,
        blank=True
    )
    stock_item = models.ForeignKey(
        StockItem,
        on_delete=models.PROTECT
    )
    quantity_used = models.DecimalField(
        max_digits=12,
        decimal_places=3
    )
    
    def __str__(self):
        return f"{self.stock_item.name}"
        return f"{self.stock_item.name} - {self.production_card.production_code}"

class Dispatch(models.Model):
    dispatch_date = models.DateField()
    customer_name = models.CharField(max_length=255)
    stock_item = models.ForeignKey(
        StockItem,
        on_delete=models.PROTECT,
        related_name='dispatches'
    )
    quantity = models.DecimalField(max_digits=12, decimal_places=3)
    notes = models.TextField(blank=True)

    created_by = models.ForeignKey(
        'UserDetail.User',
        on_delete=models.SET_NULL,
        null=True
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Dispatch - {self.stock_item.name}"

class ExpenseHead(models.Model):
    name = models.CharField(max_length=100, unique=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name

class PettyCash(models.Model):
    expense_date = models.DateField()
    expense_head = models.ForeignKey(
        ExpenseHead,
        on_delete=models.PROTECT
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    notes = models.TextField(blank=True)

    created_by = models.ForeignKey(
        'UserDetail.User',
        on_delete=models.SET_NULL,
        null=True
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.expense_head.name} - {self.amount}"
