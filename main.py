import os

from fastapi import FastAPI, Depends
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import String

from database import SessionLocal, Base, engine
from models import Cake, Order, Reviews

app = FastAPI(title = "Торты")

from fastapi.staticfiles import StaticFiles
from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext



app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # пока все, потом заменишь на свой домен
    allow_methods=["*"],
    allow_headers=["*"],
)


SECRET_KEY = "мой-секретный-ключ-который-никто-не-знает"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


fake_users_db = {
    "admin" : {
        "username": "admin",
        "password": pwd_context.hash("123"),
    }
}


class LoginData(BaseModel):
    username: str
    password: str

def create_access_token(username: str) -> str:
    # Время истечения: сейчас + 60 минут
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    # Что кладём внутрь токена
    data = {
        "sub": username,  # "sub" — кто владелец (admin)
        "exp": expire  # "exp" — когда истекает
    }
    # Создаём токен: кодируем + подписываем секретным ключом
    token = jwt.encode(data, SECRET_KEY, algorithm=ALGORITHM)
    return token


@app.post("/login")
def login(data: LoginData):
    # Ищем пользователя по логину
    user = fake_users_db.get(data.username)

    # Если не нашли — ошибка
    if not user:
        return {"error": "Неверный логин или пароль"}

    # Проверяем пароль (сравниваем с хешем)
    if not pwd_context.verify(data.password, user["password"]):
        return {"error": "Неверный логин или пароль"}

    # Создаём токен
    token = create_access_token(username=data.username)

    # Возвращаем токен
    return {"access_token": token, "token_type": "bearer"}



def verify_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        return username  # вернёт "admin" если токен настоящий
    except JWTError:
        return None




def get_db():
    db = SessionLocal()    # открыли разговор с базой
    try:
        yield db           # отдали разговор тому, кто запросил
    finally:
        db.close()         # закрыли разговор (обязательно, даже если ошибка)


@app.on_event("startup")
def startup():
    Base.metadata.create_all(bind=engine)  # создай все таблицы в базе



@app.get("/cakes")
def get_cakes(db = Depends(get_db)):
    return db.query(Cake).all()



@app.get("/cakes/{cake_id}")
def get_cake(cake_id: int, db = Depends(get_db)):
    return db.query(Cake).get(cake_id)

class CakeCreate(BaseModel):
    name: str
    price: float
    description: str = ""
    weight: float = 1.0
    persons: str = ""
    image_url: str = ""
    category: str = ""
    is_available: bool = True



@app.post("/admin/addCakes")
def add_cake(data: CakeCreate, token: str, db = Depends(get_db)):

    if not verify_token(token):
        return "Вы не админ"

    new_cake = Cake(
        name=data.name,
        price=data.price,
        description=data.description,
        weight=data.weight,
        persons=data.persons,
        image_url=data.image_url,
        category=data.category,
        is_available= data.is_available,
    )
    db.add(new_cake)
    db.commit()
    db.refresh(new_cake)
    return new_cake

@app.put("/admin/cakes/{id}")
def update_cake(id: int, data: CakeCreate,token: str, db = Depends(get_db)):
    if not verify_token(token):
        return "Вы не админ"

    cake = db.query(Cake).filter(Cake.id == id).first()
    if not cake:
        return {"error": "Торт не найден"}

    cake.name = data.name
    cake.price = data.price
    cake.description = data.description
    cake.weight = data.weight
    cake.persons = data.persons
    cake.image_url = data.image_url
    cake.category = data.category
    cake.is_available = data.is_available

    db.commit()
    db.refresh(cake)
    return cake

@app.delete("/admin/cakes/{id}")
def delete_cake(id: int, token: str, db = Depends(get_db)):
    if not verify_token(token):
        return "Вы не админ"


    cake = db.query(Cake).filter(Cake.id == id).first()
    if not cake:
        return {"message": "Торт удалён"}
    db.delete(cake)
    db.commit()

    return ("ТОрт удален")





class Orders(BaseModel):
    cake_id: int
    customer_name: str
    phone : str
    message: str


@app.post("/order")
def order(data: Orders, db = Depends(get_db)):

    newOrder = Order(
        cake_id = data.cake_id,
        customer_name = data.customer_name,
        phone = data.phone,
        message = data.message,

    )
    db.add(newOrder)
    db.commit()
    db.refresh(newOrder)
    return newOrder



@app.get("/admin/orders")
def get_admin_orders(token: str, db = Depends(get_db)):
    if not verify_token(token):
        return {"error": "Вы не админ"}
    return db.query(Order).all()


@app.delete("/admin/orders/{order_id}")
def delete_order(order_id: int, token: str, db=Depends(get_db)):
    if not verify_token(token):
        return {"error": "Вы не админ"}

    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        return {"error": "Заказ не найден"}

    db.delete(order)  # ← ОБЪЕКТ, не число!
    db.commit()
    return {"message": "Заказ удалён"}




class Reviewses(BaseModel):
    author_name: str
    text: str
    rating: int


@app.post("/reviews")
def add_reviews(reviews: Reviewses, db = Depends(get_db)):

    newReviews = Reviews(
        author_name = reviews.author_name,
        text = reviews.text,
        rating = reviews.rating
    )

    db.add(newReviews)
    db.commit()
    db.refresh(newReviews)
    return newReviews

@app.delete("/admin/reviews/{review_id}")
def delete_review(review_id: int, db = Depends(get_db)):
    review = db.query(Reviews).filter(Reviews.id == review_id).first()
    db.delete(review)
    db.commit()
    return review, " Удален"

@app.get("/reviews")
def get_reviews( db = Depends(get_db)):
    return db.query(Reviews).all()



app.mount("/", StaticFiles(directory=os.path.join(os.path.dirname(__file__), "static"), html=True), name="static")