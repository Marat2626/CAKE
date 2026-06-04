

import os
from fastapi import FastAPI, Depends, Header, HTTPException
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import String
from dotenv import load_dotenv

from database import SessionLocal, Base, engine
from models import Cake, Order, Reviews, Setting

# 🔒 Загружаем переменные окружения из .env файла
load_dotenv()

app = FastAPI(title="Торты")

from fastapi.staticfiles import StaticFiles
from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Пока для тестов все домены
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 🔒 Секретный ключ из переменных окружения
SECRET_KEY = os.getenv("SECRET_KEY", "мой-секретный-ключ-который-никто-не-знает")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# 🔒 Пароль из переменных окружения, а не в коде!
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "changeme123")

fake_users_db = {
    ADMIN_USERNAME: {
        "username": ADMIN_USERNAME,
        "password": pwd_context.hash(ADMIN_PASSWORD),
    }
}


class LoginData(BaseModel):
    username: str
    password: str


def create_access_token(username: str) -> str:
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    data = {
        "sub": username,
        "exp": expire
    }
    token = jwt.encode(data, SECRET_KEY, algorithm=ALGORITHM)
    return token


def verify_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        return username
    except JWTError:
        return None


# 🔒 Новая зависимость для проверки токена через заголовок Authorization
def get_current_admin(authorization: str = Header(None)):
    if not authorization:
        raise HTTPException(status_code=401, detail="🔒 Требуется авторизация")

    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="🔒 Неверный формат токена")

    token = authorization.replace("Bearer ", "")
    username = verify_token(token)

    if not username:
        raise HTTPException(status_code=401, detail="🔒 Неверный или истекший токен")

    return username


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.on_event("startup")
def startup():
    Base.metadata.create_all(bind=engine)


@app.post("/login")
def login(data: LoginData):
    user = fake_users_db.get(data.username)

    if not user:
        raise HTTPException(status_code=401, detail="Неверный логин или пароль")

    if not pwd_context.verify(data.password, user["password"]):
        raise HTTPException(status_code=401, detail="Неверный логин или пароль")

    token = create_access_token(username=data.username)

    return {"access_token": token, "token_type": "bearer"}


@app.get("/cakes")
def get_cakes(db=Depends(get_db)):
    return db.query(Cake).all()


@app.get("/cakes/{cake_id}")
def get_cake(cake_id: int, db=Depends(get_db)):
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


# 🔒 ИСПРАВЛЕНО: убрали token из параметров, добавили admin
@app.post("/admin/addCakes")
def add_cake(data: CakeCreate, admin: str = Depends(get_current_admin), db=Depends(get_db)):
    new_cake = Cake(
        name=data.name,
        price=data.price,
        description=data.description,
        weight=data.weight,
        persons=data.persons,
        image_url=data.image_url,
        category=data.category,
        is_available=data.is_available,
    )
    db.add(new_cake)
    db.commit()
    db.refresh(new_cake)
    return new_cake


# 🔒 ИСПРАВЛЕНО: убрали token из параметров, добавили admin
@app.put("/admin/cakes/{id}")
def update_cake(id: int, data: CakeCreate, admin: str = Depends(get_current_admin), db=Depends(get_db)):
    cake = db.query(Cake).filter(Cake.id == id).first()
    if not cake:
        raise HTTPException(status_code=404, detail="Торт не найден")

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


# 🔒 ИСПРАВЛЕНО: убрали token из параметров, добавили admin
@app.delete("/admin/cakes/{id}")
def delete_cake(id: int, admin: str = Depends(get_current_admin), db=Depends(get_db)):
    cake = db.query(Cake).filter(Cake.id == id).first()
    if not cake:
        raise HTTPException(status_code=404, detail="Торт не найден")

    db.delete(cake)
    db.commit()

    return {"message": "Торт удалён"}


class Orders(BaseModel):
    cake_id: int
    customer_name: str
    phone: str
    message: str


@app.post("/order")
def order(data: Orders, db=Depends(get_db)):
    newOrder = Order(
        cake_id=data.cake_id,
        customer_name=data.customer_name,
        phone=data.phone,
        message=data.message,
    )
    db.add(newOrder)
    db.commit()
    db.refresh(newOrder)
    return newOrder


# 🔒 ИСПРАВЛЕНО: убрали token из параметров, добавили admin
@app.get("/admin/orders")
def get_admin_orders(admin: str = Depends(get_current_admin), db=Depends(get_db)):
    return db.query(Order).all()


# 🔒 ИСПРАВЛЕНО: убрали token из параметров, добавили admin
@app.delete("/admin/orders/{order_id}")
def delete_order(order_id: int, admin: str = Depends(get_current_admin), db=Depends(get_db)):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Заказ не найден")

    db.delete(order)
    db.commit()
    return {"message": "Заказ удалён"}


class Reviewses(BaseModel):
    author_name: str
    text: str
    rating: int


@app.post("/reviews")
def add_reviews(reviews: Reviewses, db=Depends(get_db)):
    newReviews = Reviews(
        author_name=reviews.author_name,
        text=reviews.text,
        rating=reviews.rating
    )
    db.add(newReviews)
    db.commit()
    db.refresh(newReviews)
    return newReviews


# 🔒 ИСПРАВЛЕНО: добавили проверку токена (была критическая уязвимость!)
@app.delete("/admin/reviews/{review_id}")
def delete_review(review_id: int, admin: str = Depends(get_current_admin), db=Depends(get_db)):
    review = db.query(Reviews).filter(Reviews.id == review_id).first()
    if not review:
        raise HTTPException(status_code=404, detail="Отзыв не найден")

    db.delete(review)
    db.commit()
    return {"message": "Отзыв удалён"}


@app.get("/reviews")
def get_reviews(db=Depends(get_db)):
    return db.query(Reviews).all()


class SetingUpdate(BaseModel):
    head: str
    title: str
    description: str
    phone: str
    address: str
    email: str
    working_hours: str


# 🔒 ИСПРАВЛЕНО: убрали token из параметров, добавили admin
@app.post("/admin/setting")
def setting(seting: SetingUpdate, admin: str = Depends(get_current_admin), db=Depends(get_db)):
    defaults = {
        "head": seting.head,
        "title": seting.title,
        "description": seting.description,
        "phone": seting.phone,
        "address": seting.address,
        "email": seting.email,
        "working_hours": seting.working_hours,
    }

    for key, value in defaults.items():
        dbSetting = db.query(Setting).filter(Setting.key == key).first()
        if dbSetting:
            dbSetting.value = value
        else:
            db.add(Setting(key=key, value=value))
    db.commit()
    return {"message": "Настройки сохранены", "settings": defaults}


@app.get("/settings")
def get_settings(db=Depends(get_db)):
    bd = db.query(Setting).all()

    result = {}
    for setting in bd:
        result[setting.key] = setting.value

    return result


app.mount("/", StaticFiles(directory=os.path.join(os.path.dirname(__file__), "static"), html=True), name="static")