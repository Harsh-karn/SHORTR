import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    clerk_id = Column(String, unique=True, nullable=False)
    email = Column(String, nullable=False)
    plan = Column(String, default="free")
    api_calls_today = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    links = relationship("Link", back_populates="user")
    domains = relationship("Domain", back_populates="user")
    api_keys = relationship("APIKey", back_populates="user", cascade="all, delete-orphan")
    bulk_jobs = relationship("BulkJob", back_populates="user")
    subscriptions = relationship("Subscription", back_populates="user")

class Domain(Base):
    __tablename__ = "domains"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    domain = Column(String, unique=True, nullable=False)
    is_verified = Column(Boolean, default=False)
    verification_token = Column(String)
    ssl_provisioned = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    user = relationship("User", back_populates="domains")
    links = relationship("Link", back_populates="domain")

class Link(Base):
    __tablename__ = "links"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    slug = Column(String, unique=True, nullable=False)
    destination_url = Column(Text, nullable=False)
    title = Column(String)
    domain_id = Column(UUID(as_uuid=True), ForeignKey("domains.id"), nullable=True)
    is_active = Column(Boolean, default=True)
    has_analytics = Column(Boolean, default=False)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    password_hash = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="links")
    domain = relationship("Domain", back_populates="links")
    deep_link = relationship("DeepLink", back_populates="link", uselist=False)

class DeepLink(Base):
    __tablename__ = "deep_links"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    link_id = Column(UUID(as_uuid=True), ForeignKey("links.id"))
    ios_scheme = Column(String)
    ios_app_store_url = Column(String)
    android_scheme = Column(String)
    android_package = Column(String)
    android_play_store_url = Column(String)
    fallback_url = Column(String)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    link = relationship("Link", back_populates="deep_link")

class BulkJob(Base):
    __tablename__ = "bulk_jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    status = Column(String, default="pending")
    total_rows = Column(Integer)
    processed_rows = Column(Integer, default=0)
    result_file_url = Column(String)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    user = relationship("User", back_populates="bulk_jobs")

class Subscription(Base):
    __tablename__ = "subscriptions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    razorpay_subscription_id = Column(String)
    plan = Column(String, nullable=False)
    status = Column(String)
    current_period_end = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    user = relationship("User", back_populates="subscriptions")

class APIKey(Base):
    __tablename__ = "api_keys"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name = Column(Text, nullable=False)
    key_prefix = Column(Text, nullable=False)
    key_hash = Column(Text, unique=True, nullable=False, index=True)
    scopes = Column(ARRAY(Text), default=["read", "write"])
    is_active = Column(Boolean, default=True)
    last_used_at = Column(DateTime(timezone=True), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    user = relationship("User", back_populates="api_keys")
