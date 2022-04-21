from sqlalchemy import create_engine
from sqlalchemy import Column, ForeignKey, Integer, String, Date
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import Session

Base = declarative_base()
engine = create_engine("sqlite+pysqlite:///sqlite.db", echo=True, future=True)


class Entry(Base):
    __tablename__ = 'entry'

    id = Column(Integer, primary_key = True)
    name = Column(String, nullable=False)
    category = Column(String, nullable=False)
    url = Column(String, nullable=False)
    description = Column(String, nullable=False)
    keywords = Column(String, nullable=False)
    last_updated = Column(Date)


if __name__ == '__main__':
    Base.metadata.create_all(engine)

    e1 = Entry(name='pyo', category='dsp', url='http://me.org',
               description='blach blah', keywords='dsp, audio')


    with Session(engine) as session:
        session.add(e1)
        session.commit()

