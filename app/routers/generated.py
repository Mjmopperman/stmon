"""
Auto-generated FastAPI router from endpoints.yaml.
DO NOT EDIT - regenerate with: python generator.py
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from uuid import UUID
from app.hasura import hasura_client

router = APIRouter()



# =============================================================================
# Pydantic Models
# =============================================================================

class User(BaseModel):
    """User model based on user table"""
    id: Optional[int]
    email: str
    password_hash: str
    created_at: Optional[datetime]
    is_active: Optional[bool]

class Post(BaseModel):
    """Post model based on post table"""
    id: UUID
    title: str
    content: Optional[str]
    user_id: Optional[UUID]
    created_at: Optional[datetime]
    status: Optional[str]
    updated_at: Optional[datetime]
    published_at: Optional[datetime]

class Complex(BaseModel):
    """Complex model based on complex table"""
    name: str
    id: UUID

class Order(BaseModel):
    """Order model based on order table"""
    id: Optional[int]
    user_id: Optional[int]
    total: float
    created_at: Optional[datetime]
    status: Optional[str]

class Product(BaseModel):
    """Product model based on product table"""
    id: Optional[int]
    name: str
    price: float


# =============================================================================
# Endpoints
# =============================================================================


@router.post("/complex/update/{id}", status_code=201)
async def complex_update_id(id: str):
    # TODO: Implement endpoint logic
    return {"message": "Endpoint complex_update_id not implemented"}


@router.get("/product/get/{id}", response_model=Product)
async def product_get_id(id: str):
    """Get a single product by ID"""
    # TODO: Implement endpoint logic
    return {"message": "Endpoint product_get_id not implemented"}


@router.post("/product/update/{id}", response_model=Product, status_code=201)
async def product_update_id(id: str, product: Product):
    """Update a product by ID"""
    # TODO: Implement endpoint logic
    return {"message": "Endpoint product_update_id not implemented"}


@router.delete("/product/delete/{id}")
async def product_delete_id(id: str):
    """Delete a product by ID"""
    # TODO: Implement endpoint logic
    return {"message": "Endpoint product_delete_id not implemented"}


@router.get("/post/get/{id}", response_model=Post)
async def post_get_id(id: str):
    """Get a single post by ID"""
    # TODO: Implement endpoint logic
    return {"message": "Endpoint post_get_id not implemented"}


@router.post("/post/update/{id}", response_model=Post, status_code=201)
async def post_update_id(id: str, post: Post):
    """Update a post by ID"""
    # TODO: Implement endpoint logic
    return {"message": "Endpoint post_update_id not implemented"}


@router.delete("/post/delete/{id}")
async def post_delete_id(id: str):
    """Delete a post by ID"""
    # TODO: Implement endpoint logic
    return {"message": "Endpoint post_delete_id not implemented"}


@router.get("/user/list", response_model=List[User])
async def user_list():
    """List all user"""
    result = await hasura_client.query("""
        query {
            user {
                id
                    email
                    password_hash
                    created_at
                    is_active
            }
        }
    """)
    items = result.get("data", {}).get("user", [])
    return items


@router.get("/user/{id}", response_model=User)
async def user_get(id: str):
    """Get a single user by ID"""
    variables = {"id": id}
    result = await hasura_client.query("""
        query GetUser($id: Int!) {
            user(where: {id: {_eq: $id}}) {
                id
                    email
                    password_hash
                    created_at
                    is_active
            }
        }
    """, variables=variables)
    items = result.get("data", {}).get("user", [])
    if not items:
        raise HTTPException(status_code=404, detail="User not found")
    return items[0]


@router.post("/user", response_model=User, status_code=201)
async def user_create(user: User):
    """Create a new user"""
    # Build variables from request model
    data = user.model_dump(exclude_none=True)
    result = await hasura_client.query("""
        mutation CreateUser($email: String!, $password_hash: String!, $is_active: Boolean) {
            insert_user(objects: {email: $email, password_hash: $password_hash, is_active: $is_active}) {
                returning {
                    id
                    email
                    password_hash
                    created_at
                    is_active
                }
            }
        }
    """)
    items = result.get("data", {}).get("user", [])
    return items


@router.put("/user/{id}", response_model=User)
async def user_update(id: str, user: User):
    """Update a user by ID"""
    # Build variables from request model
    data = user.model_dump(exclude_none=True)
    variables = {"id": id, "id": id}
    variables.update(data)
    result = await hasura_client.query("""
        mutation UpdateUser($id: Int!, $changes: user_set_input!) {
            update_user(where: {id: {_eq: $id}}, _set: $changes) {
                returning {
                    id
                    email
                    password_hash
                    created_at
                    is_active
                }
            }
        }
    """, variables=variables)
    items = result.get("data", {}).get("user", [])
    return items


@router.delete("/user/{id}")
async def user_delete(id: str):
    """Delete a user by ID"""
    variables = {"id": id}
    result = await hasura_client.query("""
        mutation DeleteUser($id: Int!) {
            delete_user(where: {id: {_eq: $id}}) {
                affected_rows
            }
        }
    """, variables=variables)
    items = result.get("data", {}).get("user", [])
    if not items:
        raise HTTPException(status_code=404, detail="User not found")
    return items[0]


@router.get("/post/list", response_model=List[Post])
async def post_list():
    """List all post"""
    result = await hasura_client.query("""
        query {
            post {
                id
                    title
                    content
                    user_id
                    created_at
                    status
                    updated_at
                    published_at
            }
        }
    """)
    items = result.get("data", {}).get("post", [])
    return items


@router.get("/post/{id}", response_model=Post)
async def post_get(id: str):
    """Get a single post by ID"""
    variables = {"id": id}
    result = await hasura_client.query("""
        query GetPost($id: uuid!) {
            post(where: {id: {_eq: $id}}) {
                id
                    title
                    content
                    user_id
                    created_at
                    status
                    updated_at
                    published_at
            }
        }
    """, variables=variables)
    items = result.get("data", {}).get("post", [])
    if not items:
        raise HTTPException(status_code=404, detail="Post not found")
    return items[0]


@router.post("/post", response_model=Post, status_code=201)
async def post_create(post: Post):
    """Create a new post"""
    # Build variables from request model
    data = post.model_dump(exclude_none=True)
    result = await hasura_client.query("""
        mutation CreatePost($title: String!, $content: String, $user_id: uuid, $status: String) {
            insert_post(objects: {title: $title, content: $content, user_id: $user_id, status: $status}) {
                returning {
                    id
                    title
                    content
                    user_id
                    created_at
                    status
                    updated_at
                    published_at
                }
            }
        }
    """)
    items = result.get("data", {}).get("post", [])
    return items


@router.put("/post/{id}", response_model=Post)
async def post_update(id: str, post: Post):
    """Update a post by ID"""
    # Build variables from request model
    data = post.model_dump(exclude_none=True)
    variables = {"id": id, "id": id}
    variables.update(data)
    result = await hasura_client.query("""
        mutation UpdatePost($id: uuid!, $changes: post_set_input!) {
            update_post(where: {id: {_eq: $id}}, _set: $changes) {
                returning {
                    id
                    title
                    content
                    user_id
                    created_at
                    status
                    updated_at
                    published_at
                }
            }
        }
    """, variables=variables)
    items = result.get("data", {}).get("post", [])
    return items


@router.delete("/post/{id}")
async def post_delete(id: str):
    """Delete a post by ID"""
    variables = {"id": id}
    result = await hasura_client.query("""
        mutation DeletePost($id: uuid!) {
            delete_post(where: {id: {_eq: $id}}) {
                affected_rows
            }
        }
    """, variables=variables)
    items = result.get("data", {}).get("post", [])
    if not items:
        raise HTTPException(status_code=404, detail="Post not found")
    return items[0]


@router.get("/complex/list", response_model=List[Complex])
async def complex_list():
    """List all complex"""
    result = await hasura_client.query("""
        query {
            complex {
                name
                    id
            }
        }
    """)
    items = result.get("data", {}).get("complex", [])
    return items


@router.get("/complex/{id}", response_model=Complex)
async def complex_get(id: str):
    """Get a single complex by ID"""
    variables = {"id": id}
    result = await hasura_client.query("""
        query GetComplex($id: uuid!) {
            complex(where: {id: {_eq: $id}}) {
                name
                    id
            }
        }
    """, variables=variables)
    items = result.get("data", {}).get("complex", [])
    if not items:
        raise HTTPException(status_code=404, detail="Complex not found")
    return items[0]


@router.post("/complex", response_model=Complex, status_code=201)
async def complex_create(complex: Complex):
    """Create a new complex"""
    # Build variables from request model
    data = complex.model_dump(exclude_none=True)
    result = await hasura_client.query("""
        mutation CreateComplex($name: String!) {
            insert_complex(objects: {name: $name}) {
                returning {
                    name
                    id
                }
            }
        }
    """)
    items = result.get("data", {}).get("complex", [])
    return items


@router.put("/complex/{id}", response_model=Complex)
async def complex_update(id: str, complex: Complex):
    """Update a complex by ID"""
    # Build variables from request model
    data = complex.model_dump(exclude_none=True)
    variables = {"id": id, "id": id}
    variables.update(data)
    result = await hasura_client.query("""
        mutation UpdateComplex($id: uuid!, $changes: complex_set_input!) {
            update_complex(where: {id: {_eq: $id}}, _set: $changes) {
                returning {
                    name
                    id
                }
            }
        }
    """, variables=variables)
    items = result.get("data", {}).get("complex", [])
    return items


@router.delete("/complex/{id}")
async def complex_delete(id: str):
    """Delete a complex by ID"""
    variables = {"id": id}
    result = await hasura_client.query("""
        mutation DeleteComplex($id: uuid!) {
            delete_complex(where: {id: {_eq: $id}}) {
                affected_rows
            }
        }
    """, variables=variables)
    items = result.get("data", {}).get("complex", [])
    if not items:
        raise HTTPException(status_code=404, detail="Complex not found")
    return items[0]


@router.get("/order/list", response_model=List[Order])
async def order_list():
    """List all order"""
    result = await hasura_client.query("""
        query {
            order {
                id
                    user_id
                    total
                    created_at
                    status
            }
        }
    """)
    items = result.get("data", {}).get("order", [])
    return items


@router.get("/order/{id}", response_model=Order)
async def order_get(id: str):
    """Get a single order by ID"""
    variables = {"id": id}
    result = await hasura_client.query("""
        query GetOrder($id: Int!) {
            order(where: {id: {_eq: $id}}) {
                id
                    user_id
                    total
                    created_at
                    status
            }
        }
    """, variables=variables)
    items = result.get("data", {}).get("order", [])
    if not items:
        raise HTTPException(status_code=404, detail="Order not found")
    return items[0]


@router.post("/order", response_model=Order, status_code=201)
async def order_create(order: Order):
    """Create a new order"""
    # Build variables from request model
    data = order.model_dump(exclude_none=True)
    result = await hasura_client.query("""
        mutation CreateOrder($user_id: Int, $total: Float!, $status: String) {
            insert_order(objects: {user_id: $user_id, total: $total, status: $status}) {
                returning {
                    id
                    user_id
                    total
                    created_at
                    status
                }
            }
        }
    """)
    items = result.get("data", {}).get("order", [])
    return items


@router.put("/order/{id}", response_model=Order)
async def order_update(id: str, order: Order):
    """Update a order by ID"""
    # Build variables from request model
    data = order.model_dump(exclude_none=True)
    variables = {"id": id, "id": id}
    variables.update(data)
    result = await hasura_client.query("""
        mutation UpdateOrder($id: Int!, $changes: order_set_input!) {
            update_order(where: {id: {_eq: $id}}, _set: $changes) {
                returning {
                    id
                    user_id
                    total
                    created_at
                    status
                }
            }
        }
    """, variables=variables)
    items = result.get("data", {}).get("order", [])
    return items


@router.delete("/order/{id}")
async def order_delete(id: str):
    """Delete a order by ID"""
    variables = {"id": id}
    result = await hasura_client.query("""
        mutation DeleteOrder($id: Int!) {
            delete_order(where: {id: {_eq: $id}}) {
                affected_rows
            }
        }
    """, variables=variables)
    items = result.get("data", {}).get("order", [])
    if not items:
        raise HTTPException(status_code=404, detail="Order not found")
    return items[0]


@router.get("/product/list", response_model=List[Product])
async def product_list():
    """List all product"""
    result = await hasura_client.query("""
        query {
            product {
                id
                    name
                    price
            }
        }
    """)
    items = result.get("data", {}).get("product", [])
    return items


@router.get("/product/{id}", response_model=Product)
async def product_get(id: str):
    """Get a single product by ID"""
    variables = {"id": id}
    result = await hasura_client.query("""
        query GetProduct($id: Int!) {
            product(where: {id: {_eq: $id}}) {
                id
                    name
                    price
            }
        }
    """, variables=variables)
    items = result.get("data", {}).get("product", [])
    if not items:
        raise HTTPException(status_code=404, detail="Product not found")
    return items[0]


@router.post("/product", response_model=Product, status_code=201)
async def product_create(product: Product):
    """Create a new product"""
    # Build variables from request model
    data = product.model_dump(exclude_none=True)
    result = await hasura_client.query("""
        mutation CreateProduct($name: String!, $price: Float!) {
            insert_product(objects: {name: $name, price: $price}) {
                returning {
                    id
                    name
                    price
                }
            }
        }
    """)
    items = result.get("data", {}).get("product", [])
    return items


@router.put("/product/{id}", response_model=Product)
async def product_update(id: str, product: Product):
    """Update a product by ID"""
    # Build variables from request model
    data = product.model_dump(exclude_none=True)
    variables = {"id": id, "id": id}
    variables.update(data)
    result = await hasura_client.query("""
        mutation UpdateProduct($id: Int!, $changes: product_set_input!) {
            update_product(where: {id: {_eq: $id}}, _set: $changes) {
                returning {
                    id
                    name
                    price
                }
            }
        }
    """, variables=variables)
    items = result.get("data", {}).get("product", [])
    return items


@router.delete("/product/{id}")
async def product_delete(id: str):
    """Delete a product by ID"""
    variables = {"id": id}
    result = await hasura_client.query("""
        mutation DeleteProduct($id: Int!) {
            delete_product(where: {id: {_eq: $id}}) {
                affected_rows
            }
        }
    """, variables=variables)
    items = result.get("data", {}).get("product", [])
    if not items:
        raise HTTPException(status_code=404, detail="Product not found")
    return items[0]