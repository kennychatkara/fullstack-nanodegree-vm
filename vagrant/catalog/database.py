from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy import create_engine

# Create the Base class for which all of the app's db tables and db classes
# will be created relative to.
Base = declarative_base()

# Declare custom classes and tables (at the same time using SQLAlchemy's
# Declarative approach). Upon declaration completion, SQLAlchemy will
# create metadata tables (which are basically these schemas) and store
# this metadata in the Base class object's 'metadata' property
class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key = True, autoincrement = True)
    name = Column(String(80))
    email = Column(String(80))
    picture = Column(String(250))
    google_id = Column(String(80), nullable = False, unique = True)
    google_refresh_token = Column(String(250))
    items = relationship('Item', backref = 'user')

    @property
    def serialize(self):
        return {
            'id': self.id,
            'google_id': self.google_id,
            'name': self.name,
            'email': self.email,
            'picture': self.picture,
            'items': [item.serialize for item in self.items]
        }


class Category(Base):
    __tablename__ = 'categories'
    id = Column(Integer, primary_key = True, autoincrement = True)
    name = Column(String(80), nullable = False, unique = True)
    items = relationship('Item', cascade = 'all', backref = 'category')

    @property
    def serialize(self):
        return {
            'id': self.id,
            'name': self.name,
            'items': [item.serialize for item in self.items]
        }


class Item(Base):
    __tablename__ = 'items'
    id = Column(Integer, primary_key = True, autoincrement = True)
    name = Column(String(80), nullable = False)
    description = Column(String(250))
    user_id = Column(Integer, ForeignKey('users.id'))
    category_id = Column(Integer, ForeignKey('categories.id'))

    @property
    def serialize(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'user_id': self.user_id,
            'category_id': self.category_id
        }


# Create db engine that is connected to app's database
db_engine = create_engine('sqlite:///itemcatalog.db')

# Use the schemas in the Base class object's metadata property to create the
# tables if they dont yet exist in the database
Base.metadata.create_all(bind = db_engine)