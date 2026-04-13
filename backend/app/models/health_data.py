from sqlalchemy import Column, Integer, String, DateTime, Float, Boolean, ForeignKey, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class HealthMetric(Base):
    """Generic health metric for extensibility."""
    __tablename__ = "health_metrics"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    source = Column(String, nullable=False)  # whoop, withings, fitbod, etc.
    metric_type = Column(String, nullable=False)
    value = Column(Float)
    unit = Column(String)
    recorded_at = Column(DateTime(timezone=True), nullable=False)
    raw_data = Column(JSON)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="health_metrics")


class SleepRecord(Base):
    __tablename__ = "sleep_records"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    source = Column(String, nullable=False)
    external_id = Column(String)  # ID from the source platform

    start_time = Column(DateTime(timezone=True), nullable=False)
    end_time = Column(DateTime(timezone=True), nullable=False)
    total_duration_minutes = Column(Integer)
    sleep_efficiency = Column(Float)  # 0-100%

    # Sleep stages (minutes)
    deep_sleep_minutes = Column(Integer)
    light_sleep_minutes = Column(Integer)
    rem_sleep_minutes = Column(Integer)
    awake_minutes = Column(Integer)

    # Quality scores
    sleep_score = Column(Float)  # 0-100
    recovery_score = Column(Float)  # Whoop-specific

    # Biometrics during sleep
    avg_heart_rate = Column(Float)
    min_heart_rate = Column(Float)
    hrv = Column(Float)  # Heart Rate Variability in ms
    avg_spo2 = Column(Float)  # Blood oxygen %
    respiratory_rate = Column(Float)

    raw_data = Column(JSON)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="sleep_records")


class ActivityRecord(Base):
    __tablename__ = "activity_records"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    source = Column(String, nullable=False)
    external_id = Column(String)

    activity_type = Column(String)  # running, cycling, strength, etc.
    start_time = Column(DateTime(timezone=True), nullable=False)
    end_time = Column(DateTime(timezone=True))
    duration_minutes = Column(Integer)

    calories_burned = Column(Float)
    avg_heart_rate = Column(Float)
    max_heart_rate = Column(Float)
    strain_score = Column(Float)  # Whoop strain
    steps = Column(Integer)
    distance_km = Column(Float)

    # Strength specific
    workout_name = Column(String)
    sets_completed = Column(Integer)
    total_volume_kg = Column(Float)

    raw_data = Column(JSON)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="activity_records")


class NutritionRecord(Base):
    __tablename__ = "nutrition_records"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    source = Column(String, nullable=False)  # yazio, manual
    external_id = Column(String)

    recorded_date = Column(DateTime(timezone=True), nullable=False)
    meal_type = Column(String)  # breakfast, lunch, dinner, snack

    # Macros
    calories = Column(Float)
    protein_g = Column(Float)
    carbs_g = Column(Float)
    fat_g = Column(Float)
    fiber_g = Column(Float)
    sugar_g = Column(Float)

    # Micros
    sodium_mg = Column(Float)
    potassium_mg = Column(Float)
    calcium_mg = Column(Float)
    iron_mg = Column(Float)
    vitamin_c_mg = Column(Float)
    vitamin_d_iu = Column(Float)

    food_items = Column(JSON)  # list of food items with amounts
    raw_data = Column(JSON)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="nutrition_records")


class BodyMetric(Base):
    __tablename__ = "body_metrics"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    source = Column(String, nullable=False)  # renpho, withings
    external_id = Column(String)

    measured_at = Column(DateTime(timezone=True), nullable=False)

    weight_kg = Column(Float)
    bmi = Column(Float)
    body_fat_percent = Column(Float)
    muscle_mass_kg = Column(Float)
    bone_mass_kg = Column(Float)
    water_percent = Column(Float)
    visceral_fat = Column(Float)
    metabolic_age = Column(Integer)
    basal_metabolic_rate = Column(Integer)  # kcal/day

    # Withings-specific
    fat_free_mass_kg = Column(Float)
    muscle_mass_percent = Column(Float)

    # Blood pressure (Braun/Withings)
    systolic_bp = Column(Integer)
    diastolic_bp = Column(Integer)
    pulse = Column(Integer)

    raw_data = Column(JSON)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="body_metrics")


class HydrationRecord(Base):
    __tablename__ = "hydration_records"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    source = Column(String, nullable=False)  # larq, manual
    external_id = Column(String)

    recorded_at = Column(DateTime(timezone=True), nullable=False)
    amount_ml = Column(Float)
    daily_total_ml = Column(Float)
    daily_goal_ml = Column(Float)

    raw_data = Column(JSON)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="hydration_records")
