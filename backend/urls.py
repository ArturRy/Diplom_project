from django.urls import path
from backend.views import PartnerUpdate, RegisterAccount, ConfirmAccount, LoginAccount, ShopView, CategoryView, \
    UserView, ProductView, ProductInfoView, BasketView, OrderView
from django_rest_passwordreset.views import reset_password_request_token, reset_password_confirm

app_name = 'backend'
urlpatterns = [
    path('shop/update', PartnerUpdate.as_view(), name='partner-update'),
    path('user/register', RegisterAccount.as_view(), name='user-register'),

    path('user/password_reset', reset_password_request_token, name='password-reset'),
    path('user/password_reset/confirm', reset_password_confirm, name='password-reset-confirm'),
    path('user/register/confirm', ConfirmAccount.as_view(), name='user-register-confirm'),
    path('user/login', LoginAccount.as_view(), name='user-login'),
    path('shop', ShopView.as_view(), name='shop'),
    path('category', CategoryView.as_view(), name='category'),
    path('user/info', UserView.as_view(), name='user-info'),
    path('product', ProductView.as_view(), name='product'),
    path('product/info', ProductInfoView.as_view(), name='product-info'),
    path('basket', BasketView.as_view(), name='basket'),
    path('order', OrderView.as_view(), name='order'),
]
