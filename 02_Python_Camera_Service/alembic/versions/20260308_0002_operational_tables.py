"""add operational camera tables

Revision ID: 20260308_0002
Revises: 20260305_0001
Create Date: 2026-03-08
"""

from alembic import op
import sqlalchemy as sa


revision = "20260308_0002"
down_revision = "20260305_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "camera_profiles",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("name", sa.String(length=128), nullable=False, unique=True),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("readout_speed", sa.Integer(), nullable=False, server_default="500"),
        sa.Column("gain_mode", sa.String(length=32), nullable=False, server_default="1"),
        sa.Column("cooler_level", sa.Integer(), nullable=True),
        sa.Column("target_temp_c", sa.Integer(), nullable=True),
        sa.Column("bin_x", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("bin_y", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("num_x", sa.Integer(), nullable=True),
        sa.Column("num_y", sa.Integer(), nullable=True),
        sa.Column("start_x", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("start_y", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("exposure_sec", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "camera_session",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("camera_index", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("model_id", sa.Integer(), nullable=True),
        sa.Column("model_name", sa.String(length=256), nullable=True),
        sa.Column("sdk_version", sa.String(length=64), nullable=True),
        sa.Column("host_name", sa.String(length=128), nullable=True),
        sa.Column("connected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("disconnected_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="connected"),
        sa.Column("error_message", sa.Text(), nullable=True),
    )

    op.create_table(
        "exposure_job",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("session_id", sa.String(length=64), sa.ForeignKey("camera_session.id"), nullable=True),
        sa.Column("profile_id", sa.String(length=64), sa.ForeignKey("camera_profiles.id"), nullable=True),
        sa.Column("requested_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_sec", sa.Float(), nullable=False),
        sa.Column("light_frame", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("state", sa.String(length=32), nullable=False, server_default="queued"),
        sa.Column("error_code", sa.String(length=64), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
    )
    op.create_index("ix_exposure_job_requested_at", "exposure_job", ["requested_at"], unique=False)
    op.create_index("ix_exposure_job_state", "exposure_job", ["state"], unique=False)

    op.create_table(
        "exposure_image_meta",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("exposure_id", sa.String(length=64), sa.ForeignKey("exposure_job.id"), nullable=False),
        sa.Column("width", sa.Integer(), nullable=False),
        sa.Column("height", sa.Integer(), nullable=False),
        sa.Column("bit_depth", sa.Integer(), nullable=False, server_default="16"),
        sa.Column("pixel_type", sa.String(length=32), nullable=False, server_default="uint16"),
        sa.Column("orientation", sa.String(length=64), nullable=False, server_default="top_left_origin"),
        sa.Column("bin_x", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("bin_y", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("start_x", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("start_y", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("exposure_image_meta")
    op.drop_index("ix_exposure_job_state", table_name="exposure_job")
    op.drop_index("ix_exposure_job_requested_at", table_name="exposure_job")
    op.drop_table("exposure_job")
    op.drop_table("camera_session")
    op.drop_table("camera_profiles")
