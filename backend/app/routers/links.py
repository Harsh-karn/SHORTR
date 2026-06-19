from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List
from uuid import UUID

from app.database import get_db, redis_client
from app.models import Link
from app.schemas import LinkCreate, LinkResponse
from app.services.slug import generate_unique_slug

router = APIRouter(prefix="/v1/links", tags=["links"])

@router.post("/", response_model=LinkResponse, status_code=status.HTTP_201_CREATED)
async def create_link(
    link_in: LinkCreate,
    db: AsyncSession = Depends(get_db)
    # TODO: Add auth dependency
):
    slug = link_in.slug
    if not slug:
        slug = await generate_unique_slug(db, redis_client)
    else:
        # Check if custom slug is available
        result = await db.execute(select(Link).filter(Link.slug == slug))
        if result.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Slug already in use")

    new_link = Link(
        slug=slug,
        destination_url=str(link_in.destination_url),
        title=link_in.title,
        domain_id=link_in.domain_id,
        has_analytics=link_in.has_analytics,
        expires_at=link_in.expires_at,
        password_hash=link_in.password # TODO: hash password
    )
    
    db.add(new_link)
    await db.commit()
    await db.refresh(new_link)
    return new_link

@router.get("/", response_model=List[LinkResponse])
async def list_links(
    skip: int = 0, 
    limit: int = 100,
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Link).offset(skip).limit(limit))
    return result.scalars().all()

@router.get("/{link_id}", response_model=LinkResponse)
async def get_link(
    link_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Link).filter(Link.id == link_id))
    link = result.scalar_one_or_none()
    if not link:
        raise HTTPException(status_code=404, detail="Link not found")
    return link

@router.delete("/{link_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_link(
    link_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Link).filter(Link.id == link_id))
    link = result.scalar_one_or_none()
    if not link:
        raise HTTPException(status_code=404, detail="Link not found")
        
    await db.delete(link)
    await db.commit()
    
    # Invalidate cache
    await redis_client.delete(f"link:{link.slug}")
    
    return None
