import asyncio
import sqlalchemy as sa
import sqlalchemy.orm as sorm
import logging
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
import sqlalchemy.ext.asyncio as asa
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy import String, ForeignKey
from typing import List
from datetime import datetime

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

class Base(DeclarativeBase):
    pass

class Nick(Base):
    __tablename__ = "nick"
    nick: Mapped[str] = mapped_column(String(64), primary_key=True)

    def __repr__(self) -> str:
        return f"Nick(nick={self.nick})"

class Log(Base):
    __tablename__ = "log"

    id: Mapped[int] = mapped_column(primary_key=True)
    nick: Mapped[str] = mapped_column(ForeignKey("nick.nick"))
    msg: Mapped[str] = mapped_column(String(512))
    chan: Mapped[str] = mapped_column(String(64))
    timestamp: Mapped[datetime] = mapped_column(sa.DATETIME, server_default=sa.text("CURRENT_TIMESTAMP"))
    def __repr__(self) -> str:
        return f"Log(id={self.id}, nick={self.nick}, msg={self.msg})"

async def add_nick(db: asa.AsyncSession, nick: str):
    stmt = sqlite_insert(Nick).values(nick=nick).on_conflict_do_nothing()
    await db.execute(stmt)

async def add_log(db: asa.AsyncSession, chan: str, nick: str, pmsg: str):
    l = Log(chan=chan, msg=pmsg, nick=nick)
    db.add(l)

async def get_backlog(db: asa.AsyncSession, chan: str, limit: int = 10):
    stmt = sa.select(Log).where(Log.chan==chan).order_by(Log.timestamp).limit(limit)
    res = await db.scalars(stmt)
    logger.info(f"get_backlog: {res}")
    return res
async def NewEngine(dburl: str) -> tuple[asa.AsyncEngine, asa.async_sessionmaker[asa.AsyncSession]]:
    engine = create_async_engine(dburl, echo=True)
    async_session = asa.async_sessionmaker(engine)
    async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    return engine, async_session

        
