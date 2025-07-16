from django.http import JsonResponse
from .models import Category, Product
import json


def category_list(request):
    if request.method == 'GET':
        categories = Category.objects.all()
        data = list(categories.values())
        return JsonResponse(data, safe=False)

    elif request.method == 'POST':
        data = json.loads(request.body)
        category = Category.objects.create(
            name=data['name'],
            description=data.get('description', ''),
            parent_id=data.get('parent_id')
        )
        return JsonResponse({'id': category.id}, status=201)


def category_detail(request, pk):
    try:
        category = Category.objects.get(pk=pk)
    except Category.DoesNotExist:
        return JsonResponse({'error': 'Not found'}, status=404)

    if request.method == 'GET':
        data = {
            'id': category.id,
            'name': category.name,
            'description': category.description,
            'parent_id': category.parent_id
        }
        return JsonResponse(data)


def product_list(request):
    if request.method == 'GET':
        products = Product.objects.all()
        data = list(products.values())
        return JsonResponse(data, safe=False)

    elif request.method == 'POST':
        data = json.loads(request.body)
        product = Product.objects.create(
            code=data['code'],
            name=data['name'],
            description=data.get('description', ''),
            category_id=data.get('category_id')
        )
        return JsonResponse({'id': product.id}, status=201)


def product_detail(request, pk):
    try:
        product = Product.objects.get(pk=pk)
    except Product.DoesNotExist:
        return JsonResponse({'error': 'Not found'}, status=404)

    if request.method == 'GET':
        data = {
            'id': product.id,
            'code': product.code,
            'name': product.name,
            'description': product.description,
            'category_id': product.category_id,
            'created_at': product.created_at,
            'updated_at': product.updated_at
        }
        return JsonResponse(data)