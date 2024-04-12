import pytest
from model_bakery import baker
from rest_framework.test import APIClient
from backend.models import User, ConfirmEmailToken, Contact, Shop, Order, Product, ProductInfo, Category, OrderItem
from backend.serializers import ContactSerializer


@pytest.fixture
def client():
    return APIClient()


@pytest.fixture
def user_factory():
    def factory(*args, **kwargs):
        return baker.make(User, *args, **kwargs)

    return factory


@pytest.fixture
def order_item_factory():
    def factory(*args, **kwargs):
        return baker.make(OrderItem, *args, **kwargs)

    return factory


@pytest.fixture
def category_factory():
    def factory(*args, **kwargs):
        return baker.make(Category, *args, **kwargs)

    return factory


@pytest.fixture
def contact_factory():
    def factory(*args, **kwargs):
        return baker.make(Contact, *args, **kwargs)

    return factory


@pytest.fixture
def confirm_token_factory():
    def factory(*args, **kwargs):
        return baker.make(ConfirmEmailToken, *args, **kwargs)

    return factory


@pytest.fixture
def shop_factory():
    def factory(*args, **kwargs):
        return baker.make(Shop, *args, **kwargs)

    return factory


@pytest.fixture
def order_factory():
    def factory(*args, **kwargs):
        return baker.make(Order, *args, **kwargs)

    return factory


@pytest.fixture
def product_factory():
    def factory(*args, **kwargs):
        return baker.make(Product, *args, **kwargs)

    return factory


@pytest.fixture
def product_info_factory():
    def factory(*args, **kwargs):
        return baker.make(ProductInfo, *args, **kwargs)

    return factory


@pytest.mark.django_db
def test_shop_category_product(client):
    response_shop = client.get('/backend/shop')
    response_category = client.get('/backend/category')
    response_product = client.get('/backend/product')

    assert response_shop.status_code == 200
    assert response_category.status_code == 200
    assert response_product.status_code == 200


@pytest.mark.django_db
def test_create_login_user(client):
    mail = 'somemail@mail.ru'
    some_password = 'some_password12345'
    response = client.post('/backend/user/register', data={'email': mail,
                                                           'password': some_password,
                                                           'first_name': 'some_name',
                                                           'last_name': 'some_name',
                                                           'company': 'some_company',
                                                           'position': 'some_position',
                                                           'type': 'buyer'}, )

    assert response.status_code == 200
    assert response.json().get('Status') is True
    user = User.objects.get(email=mail)
    user.is_active = True
    user.save()
    login_response = client.post('/backend/user/login', data={'email': mail,
                                                              'password': some_password})

    assert login_response.status_code == 200
    assert login_response.json()['Status'] is True


@pytest.mark.django_db
def test_confirm(client, user_factory, confirm_token_factory):
    user = user_factory()
    token = confirm_token_factory(user_id=user.pk)
    response_confirm = client.post('/backend/user/register/confirm', data={'token': 'token.key',
                                                                           'email': user.email})
    assert response_confirm.status_code == 200
    assert response_confirm.json()['Status'] is False

    response = client.post('/backend/user/register/confirm', data={'email': user.email,
                                                                   'token': token.key})
    assert response.status_code == 200
    assert response.json()['Status'] is True


@pytest.mark.django_db
def test_contact(client, user_factory, contact_factory):
    user = user_factory()
    contact = contact_factory(user_id=user.pk)
    client.force_authenticate(user=user)
    serializer = ContactSerializer(contact)
    post_response = client.post('/backend/user/info', data=serializer.data)

    assert post_response.status_code == 200
    assert Contact.objects.count() == 1

    get_response = client.get('/backend/user/info')
    phone = Contact.objects.filter(user_id=user.pk).first().phone
    assert get_response.status_code == 200
    assert get_response.json()['contacts'][0]['phone'] == phone

    serializer = ContactSerializer(contact)
    patch_response = client.patch('/backend/user/info', data=serializer.data)

    assert patch_response.status_code == 200
    assert patch_response.json()['Status'] is True

    delete_resp = client.delete('/backend/user/info')

    assert delete_resp.status_code == 200


@pytest.mark.django_db
def test_basket(client, user_factory, order_factory, shop_factory, contact_factory,
                product_info_factory, product_factory, category_factory, order_item_factory):
    user = user_factory()
    contact = contact_factory(user_id=user.pk)
    # order = order_factory(user_id=user.pk)
    category = category_factory()
    shop = shop_factory()
    product = product_factory(category=category)
    product_info = product_info_factory(shop_id=shop.pk, product_id=product.pk)
    client.force_authenticate(user=user)
    post_resp = client.post('/backend/basket', data={'product_info': product_info.pk,
                                                     'quantity': 1,
                                                     'contact_id': contact.pk})
    assert post_resp.status_code == 200
    assert Order.objects.count() == 1
    assert len(Order.objects.filter(state='basket')) == 1

    get_resp = client.get('/backend/basket')

    assert get_resp.status_code == 200
    order = Order.objects.get(user_id=user.pk)
    order_item = order_item_factory(order_id=order.pk, product_info_id=product_info.pk)
    patch_resp = client.patch('/backend/basket', data={'product_info': product_info.pk,
                                                       'quantity': 2})
    # (Q(order__user=request.user.id) & Q(order__state='basket') &
    #  Q(product_info=request.data['product_info']))
    print(user.pk)
    print(order.user_id)
    print(order.state)

    print(patch_resp.json())

    assert patch_resp.status_code == 200
    assert patch_resp.json()['Status'] is True


    delete_resp = client.delete('/backend/basket', data={'product_info': product_info.pk})
    assert delete_resp.status_code == 200
    assert len(OrderItem.objects.filter(product_info=product_info.pk)) == 0

    user2 = user_factory()
    order = order_factory(user_id=user2.pk, state='basket')

    put_resp = client.put('/backend/basket')
    assert put_resp.status_code == 200
    assert put_resp.json()['Status'] is False
    assert put_resp.json()['Message'] == 'Корзина пуста'
    # order_item = order_item_factory(order_id=order.pk, quantity=1, product_info_id=product_info.pk)

    # put_resp = client.put('/backend/basket')


@pytest.mark.django_db
def test_order(client, user_factory, order_factory, shop_factory, contact_factory,
               product_info_factory, product_factory, category_factory):
    user = user_factory(type='shop')
    contact = contact_factory(user=user)
    user2 = user_factory(type='buyer')
    order2 = order_factory(user=user2, contact_id=contact.pk)
    get_resp = client.get('/backend/order')
    client.force_authenticate(user=user2)
    assert get_resp.json()['Status'] is False
    client.force_authenticate(user=user)
    get_resp = client.get('/backend/order')
    assert get_resp.status_code == 200
    for order in get_resp.json():
        assert order['user'] == user2.pk

    patch_resp = client.patch('/backend/order', data={'id': order2.pk, 'state': 'new'})
    print(patch_resp.json())
    assert patch_resp.status_code == 200
    assert patch_resp.json()['Status'] is True


@pytest.mark.django_db
def test_product_info(client, product_info_factory, product_factory, user_factory, category_factory, shop_factory):
    user = user_factory(type='shop')
    category = category_factory()
    product = product_factory(category=category)
    shop = shop_factory(user_id=user.pk)
    product_info = product_info_factory(product_id=product.pk, shop_id=shop.pk)
    client.force_authenticate(user=user)
    get_resp = client.get('/backend/product/info')
    # print(get_resp.json())
    assert get_resp.status_code == 200
    assert get_resp.json() is not None

    patch_resp = client.patch('/backend/product/info', data={'external_id': product_info.external_id})
    print(patch_resp)
    print(product_info.external_id)
    print(product_info.shop_id)
    print(shop.pk)
    assert patch_resp.json()['Status'] is True

@pytest.mark.django_db
def test_partner_update(client, user_factory):
    user = user_factory(type='shop')
    client.force_authenticate(user=user)
    url = 'https://raw.githubusercontent.com/ArturRy/Diplom_project/main/data/shop1.yaml'
    response = client.post('/backend/shop/update', data={'url': url})
    assert response.status_code == 200
    assert response.json()['Status'] is True
