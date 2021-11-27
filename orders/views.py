from django.http.response import JsonResponse
from django.shortcuts import redirect, render
from accounts.models import Account
from accounts.views import phone_number
from carts.models import CartItem
from store.models import Product
from .models import Order, OrderProduct, Payment
from .forms import OrderForm
import datetime
import json
from .send_sms import send_sms
import razorpay

# Create your views here.


def payments(request):
    body = json.loads(request.body)
    order = Order.objects.get(user=request.user, is_ordered=False, order_number=body['orderID'])
    print(order)
    
    # Store transaction details inside Payment model
    payment = Payment(
        user = request.user,
        payment_id = body['transID'],
        payment_method = body['payment_method'],
        amound_paid = order.order_total,
        status = body['status'],
    )
    payment.save()

    order.payment = payment
    order.is_ordered = True
    order.save()

    # Move to the cart items to Order Product table
    cart_items = CartItem.objects.filter(user=request.user)

    for item in cart_items:
        orderproduct = OrderProduct()
        orderproduct.order_id = order.id
        orderproduct.payment = payment
        orderproduct.user_id = request.user.id
        orderproduct.product_id = item.product_id
        orderproduct.quantity = item.quantity
        orderproduct.product_price = item.product.price
        orderproduct.ordered = True
        orderproduct.save()

        cart_item = CartItem.objects.get(id=item.id)
        product_variation = cart_item.variations.all()
        orderproduct = OrderProduct.objects.get(id=orderproduct.id)
        orderproduct.variations.set(product_variation)
        orderproduct.save()


        # Reduce the quality of the sold products
        product = Product.objects.get(id=item.product_id)
        product.stock -= item.quantity
        product.save()


    # Clear cart
    CartItem.objects.filter(user=request.user).delete()


    # Send order recieved sms to customer
    
    phone = request.user.phone_number
    print("--------PHONE NUMBER---------")
    print(phone)
    

    # Send order number and transaction id back to senddata method via json response
    data = {
        'order_number' : order.order_number,
        'transID' : payment.payment_id,
    }
    return JsonResponse(data)

client = razorpay.Client(auth=("rzp_test_fPDgsUrJCo7Fzl", "jKBDrLJcPoER9WfGikLZwNji"))

def place_order(request, total=0, quantity=0):
    current_user = request.user

    # if the cart is less than or equal to 0, then redirect back to shop
    cart_items = CartItem.objects.filter(user=current_user)
    cart_count = cart_items.count()
    if cart_count <= 0:
        return redirect('store')

    grand_total = 0
    tax = 0
    g_total = 0
    for cart_item in cart_items:
        offerprice = cart_item.product.get_price()
        total += (offerprice['price'] * cart_item.quantity)
        quantity += cart_item.quantity
    tax = (2 * total)/100
    g_total = total + tax
    grand_total = round(g_total / 70) 

    if request.method == 'POST':
        form = OrderForm(request.POST)
        if form.is_valid():
            # Store all the billing information inside Order table
            data = Order()
            data.user = current_user
            data.first_name = form.cleaned_data['first_name']
            data.last_name = form.cleaned_data['last_name']
            data.phone = form.cleaned_data['phone']
            data.email = form.cleaned_data['email']
            data.address_line_1 = form.cleaned_data['address_line_1']
            data.address_line_2 = form.cleaned_data['address_line_2']
            data.country = form.cleaned_data['country']
            data.state = form.cleaned_data['state']
            data.city = form.cleaned_data['city']
            data.order_note = form.cleaned_data['order_note']
            data.order_total = g_total
            data.tax = tax
            data.ip = request.META.get('REMOTE_ADDR')
            data.save()
            # Generate order number
            yr = int(datetime.date.today().strftime('%Y'))
            dt = int(datetime.date.today().strftime('%d'))
            mt = int(datetime.date.today().strftime('%m'))
            d = datetime.date(yr,mt,dt)
            current_date = d.strftime("%Y%m%d") #20210305
            order_number = current_date + str(data.id)
            data.order_number = order_number
            data.save()

            
            order_amount = g_total * 100
            order_currency = 'INR'
            payment_order = client.order.create(dict(amount=int(order_amount), currency=order_currency, payment_capture=1))
            payment_order_id = payment_order['id']
            


            order  = Order.objects.get(user=current_user, is_ordered=False, order_number=order_number)
            context = {
                'order' : order,
                'cart_items' : cart_items,
                'total' : total,
                'tax' : tax,
                'grand_total' : grand_total,
                'g_total' : g_total,
                'amount' : order_amount,
                'order_id' : payment_order_id,
            }
            return render(request, 'user/payments.html', context)
        else:
            print(form.errors)
    else:
        return redirect('checkout')
        
    return redirect('checkout')


def order_complete(request):
    order_number = request.GET.get('order_number')
    transID = request.GET.get('payment_id')

    try:
        order = Order.objects.get(order_number=order_number, is_ordered=True)
        ordered_products = OrderProduct.objects.filter(order_id=order.id)

        subtotal = 0
        for i in ordered_products:
            offerprice = i.product.get_price()
            subtotal += offerprice['price'] * i.quantity

        payment = Payment.objects.get(payment_id=transID)

        context = {
            'order' : order,
            'ordered_products' : ordered_products,
            'order_number' : order.order_number,
            'transID' : payment.payment_id,
            'payment' : payment,
            'subtotal' : subtotal

        }
        return render(request, 'user/order_complete.html',context)

    except(Payment.DoesNotExist, Order.DoesNotExist):
        return redirect('homepage')