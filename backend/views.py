import json
from distutils.util import strtobool
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from rest_framework.request import Request
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.validators import URLValidator
from django.db import IntegrityError
from django.db.models import Q, Sum, F
from django.http import JsonResponse, HttpResponse
from requests import get
from rest_framework.authtoken.models import Token
from rest_framework.generics import ListAPIView
from rest_framework.response import Response
from rest_framework.views import APIView
from ujson import loads as load_json
from yaml import load as load_yaml, Loader
from rest_framework.response import Response

from backend.models import Shop, Category, Product, ProductInfo, Parameter, ProductParameter, Order, OrderItem, \
    Contact, ConfirmEmailToken, User
from backend.serializers import UserSerializer, ShopSerializer, CategorySerializer, ContactSerializer, \
    ProductSerializer, ProductInfoSerializer, OrderSerializer, OrderItemSerializer


class RegisterAccount(APIView):
    """
    Для регистрации пользователей
    """

    def post(self, request, *args, **kwargs):
        """
        Регистрирует пользователя и возврящает токен для подтверждения

        """

        if {'first_name', 'last_name', 'email', 'password', 'company', 'position', 'type'}.issubset(request.data):

            try:
                validate_password(request.data['password'])
            except Exception as password_error:
                error_array = []
                # noinspection PyTypeChecker
                for item in password_error:
                    error_array.append(item)
                return JsonResponse({'Status': False, 'Errors': {'password': error_array}})
            else:

                user_serializer = UserSerializer(data=request.data)
                if user_serializer.is_valid():

                    user = user_serializer.save()
                    user.set_password(request.data['password'])
                    user.save()
                    ConfirmEmailToken.objects.create(user_id=user.id)
                    token = ConfirmEmailToken.objects.get(user_id=user.id)
                    return JsonResponse({'Status': True, 'Token': f'{token.key}'})
                else:
                    return JsonResponse({'Status': False, 'Errors': user_serializer.errors})

        return JsonResponse({'Status': False, 'Errors': 'Не указаны все необходимые аргументы'})


class ConfirmAccount(APIView):
    """
    Класс для подтверждения почтового адреса
    """

    # Регистрация методом POST
    def post(self, request, *args, **kwargs):
        """
            Подтверждает почтовый адрес пользователя.
        """
        # проверяем обязательные аргументы
        if {'email', 'token'}.issubset(request.data):

            token = ConfirmEmailToken.objects.filter(user__email=request.data['email'],
                                                     key=request.data['token']).first()
            if token:
                token.user.is_active = True
                token.user.save()
                token.delete()
                return JsonResponse({'Status': True})
            else:
                return JsonResponse({'Status': False, 'Errors': 'Неправильно указан токен или email'})

        return JsonResponse({'Status': False, 'Errors': 'Не указаны все необходимые аргументы'})


class LoginAccount(APIView):
    """
    Класс для авторизации пользователей
    """

    def post(self, request, *args, **kwargs):
        """
        Авторизует пользователя, возвращает токен аутентификации
        """
        if {'email', 'password'}.issubset(request.data):
            user = authenticate(request, username=request.data['email'], password=request.data['password'])

            if user is not None:
                if user.is_active:
                    token, _ = Token.objects.get_or_create(user=user)

                    return JsonResponse({'Status': True, 'Token': token.key})

            return JsonResponse({'Status': False, 'Errors': 'Не удалось авторизовать'})

        return JsonResponse({'Status': False, 'Errors': 'Не указаны все необходимые аргументы'})


class ShopView(ListAPIView):
    """
    Возвращает список магазинов
    """
    queryset = Shop.objects.all()
    serializer_class = ShopSerializer


class CategoryView(ListAPIView):
    """
    Возвращает список категорий
    """
    queryset = Category.objects.all()
    serializer_class = CategorySerializer


class PartnerUpdate(APIView):
    """
    Класс для обновления прайса от поставщика
    """

    def post(self, request, *args, **kwargs):

        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, 'Error': 'Требуется пройти аутентификацию'}, status=403)

        if request.user.type != 'shop':
            return JsonResponse({'Status': False, 'Error': 'Только для магазинов'}, status=403)

        url = request.data.get('url')

        if url:
            validate_url = URLValidator()
            try:
                validate_url(url)
            except ValidationError as e:
                return JsonResponse({'Status': False, 'Error': str(e)})
            else:
                stream = get(url).content

                data = load_yaml(stream, Loader=Loader)

                shop, _ = Shop.objects.get_or_create(name=data['shop'], user_id=request.user.id)
                for category in data['categories']:
                    category_object, _ = Category.objects.get_or_create(id=category['id'], name=category['name'])
                    category_object.shops.add(shop.id)
                    category_object.save()
                ProductInfo.objects.filter(shop_id=shop.id).delete()
                for item in data['goods']:
                    product, _ = Product.objects.get_or_create(name=item['name'], category_id=item['category'])

                    product_info = ProductInfo.objects.create(product_id=product.id,
                                                              external_id=item['id'],
                                                              model=item['model'],
                                                              price=item['price'],
                                                              price_rrc=item['price_rrc'],
                                                              quantity=item['quantity'],
                                                              shop_id=shop.id)
                    for name, value in item['parameters'].items():
                        parameter_object, _ = Parameter.objects.get_or_create(name=name)
                        ProductParameter.objects.create(product_info_id=product_info.id,
                                                        parameter_id=parameter_object.id,
                                                        value=value)

                return JsonResponse({'Status': True})

        return JsonResponse({'Status': False, 'Errors': 'Не указаны все необходимые аргументы'})


class UserView(APIView):
    """
    Для добавления контактов пользователя
    """

    def get(self, request: Request, *args, **kwargs):
        """
        Для получения информации о контактах пользователя

        """
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, 'Error': 'Требуется пройти аутентификацию'}, status=403)

        serializer = UserSerializer(request.user)
        return Response(serializer.data)

    def post(self, request: Request, *args, **kwargs):
        """
        Для добавления контактов пользователя

        """
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, 'Error': 'Требуется пройти аутентификацию'}, status=403)

        user = Contact.objects.filter(user_id=request.user.id)
        if user:
            return JsonResponse({'Status': False,
                                 'Error': 'Повторное добавление данных запрещено, '
                                          'воспользуйтесь методом обновления данных'})
        if {'city', 'street', 'phone'}.issubset(request.data):
            data = request.data.copy()
            data.update({'user': request.user.id})
            serializer = ContactSerializer(data=data)

            if serializer.is_valid():
                serializer.save()
                return JsonResponse({'Status': True})
            else:
                return JsonResponse({'Status': False, 'Errors': serializer.errors})

        return JsonResponse({'Status': False, 'Errors': 'Не указаны все необходимые аргументы'})

    def patch(self, request: Request, *args, **kwargs):
        """
        Для обновления данных контактов пользователя

        """
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, 'Error': 'Требуется пройти аутентификацию'}, status=403)
        contact = Contact.objects.filter(user_id=request.user.id).first()

        if contact:
            copy_request_data = request.data.copy()
            copy_request_data.update({'user': request.user.id})

            serializer = ContactSerializer(contact, data=copy_request_data, partial=True)
            if serializer.is_valid():
                serializer.save()

                return JsonResponse({'Status': True})
            else:
                return JsonResponse({'Status': False, 'Errors': serializer.errors})
        return JsonResponse({'Status': False, 'Erros': 'Не указаны необходимые параметры'})

    def delete(self, request: Request, *args, **kwargs):
        """
        Для удаления контактов пользователя

        """
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, 'Error': 'Требуется пройти аутентификацию'})
        contact = Contact.objects.filter(user_id=request.user.id)
        contact.delete()
        return JsonResponse({'Status': True})


class ProductView(ListAPIView):
    """
    Для получения списка всех товаров
    """
    queryset = Product.objects.all()
    serializer_class = ProductSerializer


class ProductInfoView(APIView):

    def get(self, request: Request, *args, **kwargs):
        """
        Для получения списка и информации о товарах пользователя

        """

        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, 'Error': 'Требуется пройти аутентификацию'})
        if request.user.type == 'shop':

            shop = Shop.objects.filter(user_id=request.user.pk).first()

            products = ProductInfo.objects.filter(shop_id=shop.pk)
            serializer = ProductInfoSerializer(products, many=True)
            return Response(serializer.data)

        else:
            return JsonResponse({'Status': False, 'Message': 'Только для магазинов'})

    def patch(self, request: Request, *args, **kwargs):
        """
        Для редактирования информации о продукте

        """
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, 'Error': 'Требуется пройти аутентификацию'})
        shop = Shop.objects.filter(user_id=request.user.pk).first()
        if {'external_id'}.issubset(request.data):
            # request.data._mutable = True
            product = ProductInfo.objects.filter(
                Q(shop_id=shop.pk) & Q(external_id=request.data.get('external_id'))).first()
            if product:
                # request.data._mutable = True
                serializer = ProductInfoSerializer(product, data=request.data, partial=True)
                if serializer.is_valid():
                    serializer.save()
                    return JsonResponse({'Status': True})
                else:
                    return JsonResponse({'Status': False, 'Errors': serializer.errors})
        return JsonResponse({'Status': False, 'Erros': 'Не указаны необходимые параметры'})


class BasketView(APIView):

    def get(self, request: Request, *args, **kwargs):

        """
        Функция для получения информации о товарах в корзине

        """
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, 'Error': 'Требуется пройти аутентификацию'})
        orders = OrderItem.objects.filter(Q(order__user_id=request.user.id) & Q(order__state='basket'))
        if orders:
            total_price = 0
            for order in orders:
                price = order.product_info.price
                quantity = order.quantity
                total_price += price * quantity

            serializer = OrderItemSerializer(orders, many=True)
            return Response({f'Total price': {total_price}, 'Products': serializer.data})
        return JsonResponse({'Status': False, 'Error': 'У вас нет заказов'})

    def post(self, request: Request, *args, **kwargs):
        """
        Функция для добавления товаров в корзину

        """
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, 'Error': 'Требуется пройти аутентификацию'})

        if {'product_info', 'quantity', 'contact_id'}.issubset(request.data):
            try:
                basket, _ = Order.objects.get_or_create(user_id=request.user.id,
                                                        state='basket',
                                                        contact_id=request.data['contact_id'])
                need_quantity = int(request.data['quantity'])
                fact_quantity = int(ProductInfo.objects.get(id=request.data['product_info']).quantity)

                if (fact_quantity - need_quantity) >= 0:
                    data = request.data.copy()
                    data.update({'order': basket.id})
                    serializer = OrderItemSerializer(data=data)

                    if serializer.is_valid():
                        serializer.save()
                        return JsonResponse({'Status': True, 'Message': 'Товар добавлен в корзину'})
                else:
                    return JsonResponse({'Status': False, 'Message': 'Недостаточно товара на складе'})
            except:
                return JsonResponse({'Status': False})
        return JsonResponse({'Status': False, 'Message': 'Не указаны необходимые параметры'})

    def patch(self, request: Request, *args, **kwargs):

        """
        Функция для обновления колличества товаров в корзине

        """

        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, 'Error': 'Требуется пройти аутентификацию'})

        if {'product_info', 'quantity'}.issubset(request.data):
            order_item = OrderItem.objects.filter(Q(order__user=request.user.id) & Q(order__state='basket') &
                                                  Q(product_info=request.data['product_info']))
            need_quantity = int(request.data['quantity'])
            fact_quantity = int(ProductInfo.objects.get(id=request.data['product_info']).quantity)
            if order_item:
                if (fact_quantity - need_quantity) >= 0:
                    order_item.update(quantity=request.data['quantity'])
                    return JsonResponse({'Status': True, 'Message': 'Заказ обновлен'})
                else:
                    return JsonResponse({'Status': False, 'Message': 'Недостаточно товара на складе'})
        return JsonResponse({'Status': False, 'Message': 'Не указаны необходимые параметры'})

    def delete(self, request: Request, *args, **kwargs):

        """
        Функция для удаления товаров из корзины

        """
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, 'Error': 'Требуется пройти аутентификацию'})
        if {'product_info'}.issubset(request.data):
            order_item = OrderItem.objects.filter(Q(order__user=request.user.id) & Q(order__state='basket') &
                                                  Q(product_info=request.data['product_info']))
            if order_item:
                order_item.delete()
                return JsonResponse({'Status': True, 'Message': 'Товар удален из корзины'})
            return JsonResponse({'Status': False, 'Message': 'Товар не найден'})
        return JsonResponse({'Status': False, 'Message': 'Не указаны необходимые параметры'})

    def put(self, request: Request, *args, **kwargs):
        """
        Функция для передачи заказа поставщику
        Сверяет и редактирует колличество товара у поставщика при успешном запросе

        """
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, 'Error': 'Требуется пройти аутентификацию'})

        try:
            order = Order.objects.get(Q(user_id=request.user.id), Q(state='basket'))
        except:
            return JsonResponse({'Status': False, 'Message': 'Заказа со статусом корзины не существует'})

        order_items = OrderItem.objects.filter(order_id=order.id)
        if order_items:
            for order_item in order_items:
                need_quantity = int(order_item.quantity)
                fact_quantity = int(ProductInfo.objects.get(id=order_item.product_info.id).quantity)
                quantity = fact_quantity - need_quantity

                if quantity >= 0:
                    continue

                else:
                    return JsonResponse({'Status': False,
                                         'Message': 'Недостаточно товара на складе',
                                         'Товар': f'{order_item.product_info.model}'})

            for order_item in order_items:
                need_quantity = int(order_item.quantity)
                fact_quantity = int(ProductInfo.objects.get(id=order_item.product_info.id).quantity)
                quantity = fact_quantity - need_quantity
                product = ProductInfo.objects.get(id=order_item.product_info.id)
                product.quantity = quantity
                product.save()

            order.state = 'new'
            order.save()
            ConfirmEmailToken.objects.create(user_id=request.user.id)
            token = ConfirmEmailToken.objects.get(user_id=request.user.id)
            return JsonResponse({'Status': True,
                                 'Message': f'Заказ передан в обработку. Подтвердите ваш email',
                                 'Token': f'{token.key}'})

        return JsonResponse({'Status': False, 'Message': 'Корзина пуста'})


class OrderView(APIView):

    def get(self, request: Request, *args, **kwargs):
        """
        Функция для получения информации  о заказе поставщиком
        Автоматически меняет статус заказа с new на confirmed, если статус подтвержден

        """
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, 'Error': 'Требуется пройти аутентификацию'})
        if request.user.type != 'shop':
            return JsonResponse({'Status': False, 'Message': 'Только для магазинов'})
        orders = Order.objects.filter(Q(contact_id__user_id=request.user.id))
        if orders:
            for order in orders:
                if order.state == 'new' and len(ConfirmEmailToken.objects.filter(user_id=order.user_id)) == 0:
                    order.state = 'confirmed'
                    order.save()
                    user = User.objects.get(id=order.user_id)

                    msg = EmailMultiAlternatives(
                        # title:
                        f"Обновление статуса заказа",
                        # message:
                        f'Статус заказа изменен: {order.state}',
                        # from:
                        settings.EMAIL_HOST_USER,
                        # to:
                        [user.email]
                    )
                    msg.send()

            serializer = OrderSerializer(orders, many=True)
            return Response(serializer.data)

        else:
            return JsonResponse({'Status': False, 'Message': 'У Вас нет заказов'})

    def patch(self, request: Request, *args, **kwargs):
        """
        Функция для изменения статуса заказа поставщиком

        """

        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, 'Error': 'Требуется пройти аутентификацию'})
        if request.user.type != 'shop':
            return JsonResponse({'Status': False, 'Message': 'Только для магазинов'})
        orders = Order.objects.filter(contact_id__user_id=request.user.id).exclude(state='basket').exclude(state='new')
        if {'id', 'state'}.issubset(request.data):
            try:
                order = orders.get(id=request.data['id'])
                order.state = request.data['state']
                order.save()
                user = User.objects.get(id=order.user_id)

                msg = EmailMultiAlternatives(
                    # title:
                    f"Обновление статуса заказа",
                    # message:
                    f'Статус заказа изменен на {order.state}',
                    # from:
                    settings.EMAIL_HOST_USER,
                    # to:
                    [user.email]
                )
                msg.send()
            except:
                return JsonResponse({'Status': False, 'Message': 'Заказ не найден'})

            return JsonResponse({'Status': True, 'Message': f'Статус изменен на: {order.state}'})
