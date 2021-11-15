from django.forms import ModelForm

from .models import Product

class ProductForm(ModelForm):
    class Meta:
        model = Product
        fields = ['product_name', 'description', 'stock', 'price', 'category', 'images']

    def __init__(self , *args , **kwargs):
        super(ProductForm, self).__init__(*args , **kwargs)
        self.fields['product_name'].widget.attrs['placeholder'] = 'Enter Product Name'
        self.fields['description'].widget.attrs['placeholder'] = 'Enter Description'
        self.fields['stock'].widget.attrs['placeholder'] = 'Enter stock'
        self.fields['price'].widget.attrs['placeholder'] = 'Enter price'
        self.fields['category'].widget.attrs['placeholder'] = 'Select category'
        
       
        for field in self.fields:
            self.fields[field].widget.attrs['class'] = 'form-control mt-1 mb-2' 