from typing import Annotated

from fastapi import Depends
from sqlmodel import Session

from app.core.database import get_session
from app.core.security import TokenData, get_current_active_user

# Database session dependency
SessionDep = Annotated[Session, Depends(get_session)]

# Current active user dependency
# Returns TokenData object of the authenticated user
CurrentUserDep = Annotated[TokenData, Depends(get_current_active_user)]
