from typing import Generic, TypeVar

from sqlalchemy import delete, exc, select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src import exceptions
from src.db.models import Bind, Channel, User
from src.settings import DATABASE_URL

engine = create_async_engine(DATABASE_URL, echo=False)
async_session = async_sessionmaker(engine, expire_on_commit=False)

T = TypeVar("T")


class BaseRepository(Generic[T]):
    """Базовый репозиторий. Позволяет создавать объект в БД."""

    def __init__(self, model: T, session: AsyncSession) -> None:
        self._model = model
        self._session = session

    async def create(self, new_data: T) -> T:
        """Создает объект текущей модели и возвращает его, иначе возвращает ошибку ObjectAlreadyExistsError."""
        try:
            self._session.add(new_data)
            await self._session.commit()
        except exc.IntegrityError as e:
            await self._session.rollback()
            raise exceptions.ObjectAlreadyExistsError(new_data) from e
        else:
            await self._session.refresh(new_data)
            return new_data
        finally:
            await self._session.close()


class UserRepository(BaseRepository[User]):
    """Репозиторий для работы с моделью User в БД."""

    def __init__(self) -> None:
        super().__init__(User, async_session())

    async def get(self, account_id: int) -> User:
        """Возвращает объект User из БД по его account_id, иначе возвращает ошибку UserNotFoundError."""
        try:
            user = await self._session.scalars(select(self._model).where(self._model.account_id == account_id))
            return user.one()
        except exc.NoResultFound as e:
            raise exceptions.UserNotFoundError(account_id) from e
        finally:
            await self._session.close()


class ChannelRepository(BaseRepository[Channel]):
    """Репозиторий для работы с моделью Channel в БД."""

    def __init__(self) -> None:
        super().__init__(Channel, async_session())

    async def get(self, channel_id: int) -> Channel:
        """Возвращает объект Channel из БД по его channel_id, иначе возвращает ошибку ChannelNotFoundError."""
        try:
            channel = await self._session.scalars(select(self._model).where(self._model.channel_id == channel_id))
            return channel.one()
        except exc.NoResultFound as e:
            raise exceptions.ChannelNotFoundError(channel_id) from e
        finally:
            await self._session.close()


class BindRepository(BaseRepository[Bind]):
    """Репозиторий для работы с моделью Bind в БД."""

    def __init__(self) -> None:
        super().__init__(Bind, async_session())

    async def update_description(self, user_id: int, channel_id: int, new_description: str) -> None:
        """Обновляет описание у Bind с полученными user_id и channel_id."""
        await self._session.execute(
            update(self._model)
            .where(self._model.user_id == user_id and self._model.channel_id == channel_id)
            .values(description=new_description),
        )
        await self._session.commit()
        await self._session.close()

    async def remove(self, user_id: int, channel_id: int) -> None:
        """Удаляет связь канала и пользователя."""
        await self._session.execute(
            delete(self._model).where(self._model.user_id == user_id and self._model.channel_id == channel_id),
        )
        await self._session.commit()
        await self._session.close()


user_repository = UserRepository()
channel_repository = ChannelRepository()
bind_repository = BindRepository()
