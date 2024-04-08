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

    # contact.street = 'some_street'
    #
    # serializer = ContactSerializer(contact)
    # patch_response = client.patch('/backend/user/contacts')
    # print(serializer.data)
    # assert patch_response.status_code == 200
    # assert patch_response.json()['contacts'][0]['street'] == 'some_street'


@pytest.mark.django_db
def test_basket(client, user_factory, order_factory, shop_factory, contact_factory,
                product_info_factory, product_factory, category_factory):
    user = user_factory()
    contact = contact_factory(user_id=user.pk)
    # order = order_factory(user_id=user.pk)
    category = category_factory()
    shop = shop_factory()
    product = product_factory(category=category)
    product_info = product_info_factory(shop_id=shop.pk, product_id=product.pk)
    client.force_authenticate(user=user)
    post_resp = client.post('/backend/basket', data={'product_info': product_info.id,
                                                     'quantity': 1,
                                                     'contact_id': contact.pk})
    assert post_resp.status_code == 200
    assert Order.objects.count() == 1
    assert len(Order.objects.filter(state='basket')) == 1

    get_resp = client.get('/backend/basket')

    assert get_resp.status_code == 200

    patch_resp = client.patch('/backend/basket', data={'product_info': product_info.id,
                                                       'quantity': 2})
    assert patch_resp.status_code == 200

