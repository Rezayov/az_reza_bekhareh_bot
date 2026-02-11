from __future__ import annotations

import logging
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import Dispute, DisputeStatus

logger = logging.getLogger(__name__)


async def create_dispute(
    session: AsyncSession,
    listing_id: int,
    buyer_id: int,
    seller_id: int,
    reason: str,
    evidence_file_id: Optional[str],
) -> Dispute:
    dispute = Dispute(
        listing_id=listing_id,
        buyer_id=buyer_id,
        seller_id=seller_id,
        reason=reason,
        evidence_file_id=evidence_file_id,
    )
    session.add(dispute)
    await session.flush()
    logger.info("Dispute %s created", dispute.id)
    return dispute


async def list_open_disputes(session: AsyncSession) -> List[Dispute]:
    result = await session.execute(select(Dispute).where(Dispute.status.in_([DisputeStatus.open, DisputeStatus.in_review])))
    return result.scalars().all()


async def set_dispute_status(session: AsyncSession, dispute_id: int, status: DisputeStatus) -> Dispute:
    dispute = await session.get(Dispute, dispute_id)
    if dispute is None:
        raise ValueError("اختلاف پیدا نشد.")
    dispute.status = status
    await session.flush()
    logger.info("Dispute %s set to %s", dispute_id, status.value)
    return dispute
