"""extend camera_profiles with connection parameters

Revision ID: 20260309_0003
Revises: 20260308_0002
Create Date: 2026-03-09
"""

from alembic import op
import sqlalchemy as sa


revision = "20260309_0003"
down_revision = "20260308_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "camera_profiles",
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.add_column(
        "camera_profiles",
        sa.Column("sdk_camera_address", sa.String(length=128), nullable=False, server_default=""),
    )
    op.add_column(
        "camera_profiles",
        sa.Column("sdk_camera_port", sa.Integer(), nullable=False, server_default="12345"),
    )
    op.add_column(
        "camera_profiles",
        sa.Column("sdk_camera_interface", sa.Integer(), nullable=False, server_default="-1"),
    )
    op.add_column(
        "camera_profiles",
        sa.Column("sdk_camera_index", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "camera_profiles",
        sa.Column("temperature_hardware_option", sa.Integer(), nullable=False, server_default="42223"),
    )


def downgrade() -> None:
    op.drop_column("camera_profiles", "temperature_hardware_option")
    op.drop_column("camera_profiles", "sdk_camera_index")
    op.drop_column("camera_profiles", "sdk_camera_interface")
    op.drop_column("camera_profiles", "sdk_camera_port")
    op.drop_column("camera_profiles", "sdk_camera_address")
    op.drop_column("camera_profiles", "is_active")
