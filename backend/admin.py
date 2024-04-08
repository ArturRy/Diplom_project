from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from backend.models import *


# Register your models here.

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    model = User
    fieldsets = (
        ('Пользователь', {'fields': ('email', 'password', 'type')}),
        ('Персональные данные', {'fields': ('first_name', 'last_name', 'company', 'position')}),
        ('Права', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('История', {'fields': ('last_login', 'date_joined')}),
    )

    list_display = ('id', 'email', 'first_name', 'last_name', 'is_staff')
    search_fields = ('first_name', 'last_name')
    list_filter = ('last_name', 'is_staff')


@admin.register(Shop)
class ShopAdmin(admin.ModelAdmin):
    model = Shop
    list_display = ('id', 'name', 'url', 'user', 'state')
    ordering = ('-name',)
    search_fields = ('user',)


class ProductInline(admin.TabularInline):
    model = Product
    extra = 1


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    model = Category
    inlines = [ProductInline]
    list_display = ('name',)


class ProductInfoInline(admin.TabularInline):
    model = ProductInfo
    extra = 1


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    pass
    model = Product
    inlines = [ProductInfoInline]
    list_display = ('id', 'name',)


class ProductParameterInlines(admin.TabularInline):
    model = ProductParameter
    extra = 1


@admin.register(ProductInfo)
class ProductInfoAdmin(admin.ModelAdmin):
    model = ProductInfo
    fieldsets = (
        ('Основная информация', {'fields': ('product', 'model',)}),
        ('Дополнительная информация', {'fields': ('external_id', 'quantity', 'shop')}),
        ('Цены', {'fields': ('price', 'price_rrc')})
    )
    search_fields = ('external_id', 'name',)
    list_display = ('id', 'product', 'shop', 'price')
    list_filter = ('price',)
    inlines = [ProductParameterInlines]


@admin.register(Parameter)
class ParameterAdmin(admin.ModelAdmin):
    model = Parameter
    # list_display = ('id', 'name',)
    search_fields = ('category', 'name')


@admin.register(Contact)
class ContactAdmin(admin.ModelAdmin):
    fieldsets = (
        ('Основная информация', {'fields': ('user', 'phone')}),
        ('Адрес', {'fields': ('city', 'street', 'house', 'structure', 'building', 'apartment', )})
    )

    list_display = ('id', 'user', 'phone')
    search_fields = ('city', )
    ordering = ('city',)


class OrderItemInlines(admin.TabularInline):
    model = OrderItem
    extra = 1


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'state', 'dt')
    search_fields = ('user', 'state')
    ordering = ('-dt',)
    inlines = [OrderItemInlines]

