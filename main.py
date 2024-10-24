from fastapi import FastAPI, HTTPException, status, Query
from fastapi.responses import JSONResponse
from typing import Annotated, Dict, Any, List
from pydantic import BaseModel, NonNegativeFloat, NonNegativeInt, PositiveInt
from lecture_2.hw.shop_api.models import Item, Cart, CartItem, ItemPost

app = FastAPI(title="Shop API")

items_db: Dict[int, Item] = {}
carts_db: Dict[int, Cart] = {}


class CartResponse(BaseModel):
    id: int
    items: List[CartItem]
    price: float


class ItemResponse(BaseModel):
    id: int
    name: str
    price: float


@app.post("/item", status_code=status.HTTP_201_CREATED, response_model=ItemResponse)
def create_item(item: ItemPost):
    item_id = len(items_db) + 1
    new_item = Item(id=item_id, name=item.name, price=item.price)
    items_db[item_id] = new_item
    return JSONResponse(
        content={"id": new_item.id, "name": new_item.name, "price": new_item.price},
        status_code=status.HTTP_201_CREATED,
        headers={"Location": f"/item/{item_id}"})


@app.get("/item/{id}", response_model=ItemResponse, status_code=status.HTTP_200_OK)
def get_item(id: int):
    item = items_db.get(id)
    if not item or item.deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    return item


@app.get("/item", response_model=List[ItemResponse])
def get_item_list(offset: Annotated[NonNegativeInt, Query()] = 0,
                  limit: Annotated[PositiveInt, Query()] = 10,
                  min_price: Annotated[NonNegativeFloat, Query()] = None,
                  max_price: Annotated[NonNegativeFloat, Query()] = None,
                  show_deleted: bool = False):

    filtered_items_db = [item for item in list(items_db.values())[offset:offset + limit]
                      if (show_deleted or not item.deleted) and
                      (min_price is None or item.price >= min_price) and
                      (max_price is None or item.price <= max_price)]
    return filtered_items_db


@app.put("/item/{id}", response_model=ItemResponse)
def update_item(id: int, item: ItemPost):
    if id not in items_db:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    new_item = Item(id=id, name=item.name, price=item.price)
    items_db[id] = new_item
    return new_item


@app.patch("/item/{id}", response_model=ItemResponse)
def patch_item(id: int, body: dict[str, Any]):
    item = items_db.get(id)
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    if item.deleted:
        raise HTTPException(status_code=status.HTTP_304_NOT_MODIFIED, detail="Item is deleted")

    allowed_fields = {"name", "price"}
    for key, value in body.items():
        if key in allowed_fields:
            setattr(item, key, value)
        else:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                                detail="Invalid field in request body")
    return item


@app.delete("/item/{id}")
def delete_item(id: int):
    if id not in items_db:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    items_db[id].deleted = True
    return {"message": "Item marked as deleted"}


@app.post("/cart", status_code=status.HTTP_201_CREATED)
def create_cart():
    cart_id = len(carts_db) + 1
    carts_db[cart_id] = Cart(id=cart_id)
    return JSONResponse(content={"id": cart_id},
                        status_code=status.HTTP_201_CREATED,
                        headers={"Location": f"/cart/{cart_id}"})


@app.get("/cart/{id}", response_model=CartResponse)
def get_cart(id: int):
    if id not in carts_db:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cart not found")
    return carts_db[id]


@app.get("/cart", response_model=List[CartResponse])
def get_cart_list(offset: Annotated[NonNegativeInt, Query()] = 0,
                  limit: Annotated[PositiveInt, Query()] = 10,
                  min_price: Annotated[NonNegativeFloat, Query()] = None,
                  max_price: Annotated[NonNegativeFloat, Query()] = None,
                  min_quantity: Annotated[NonNegativeInt, Query()] = None,
                  max_quantity: Annotated[NonNegativeInt, Query()] = None):

    filtered_carts_db = [cart for cart in list(carts_db.values())[offset:offset + limit]
                      if (min_price is None or cart.price >= min_price) and
                      (max_price is None or cart.price <= max_price) and
                      (min_quantity is None or sum(item.quantity for item in cart.items) >= min_quantity) and
                      (max_quantity is None or sum(item.quantity for item in cart.items) <= max_quantity)]
    return filtered_carts_db


@app.post("/cart/{cart_id}/add/{item_id}")
def add_to_cart(cart_id: int, item_id: int):
    if cart_id not in carts_db:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cart not found")
    if item_id not in items_db or items_db[item_id].deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found or deleted")

    item = items_db[item_id]
    cart = carts_db[cart_id]
    for cart_item in cart.items:
        if cart_item.id == item.id:
            cart_item.quantity += 1
            break
    else:
        cart.items.append(CartItem(id=item.id, name=item.name, quantity=1))
    cart.price += item.price
    return cart
