CREATE TABLE IF NOT EXISTS public.machines (
    id serial4 PRIMARY KEY,
    code varchar(40) NOT NULL UNIQUE,
    name varchar(140) NOT NULL,
    machine_type varchar(100) NOT NULL,
    area varchar(100) NOT NULL,
    max_usage_hours double precision NOT NULL CHECK (max_usage_hours > 0),
    max_vibration double precision NOT NULL CHECK (max_vibration > 0),
    max_temperature double precision NOT NULL,
    rated_current double precision NOT NULL CHECK (rated_current > 0),
    nominal_rpm double precision NOT NULL CHECK (nominal_rpm >= 0),
    max_pressure double precision NOT NULL CHECK (max_pressure >= 0),
    active boolean NOT NULL DEFAULT true,
    created_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS public.products (
    id serial4 PRIMARY KEY,
    code varchar(40) NOT NULL UNIQUE,
    name varchar(140) NOT NULL,
    product_type varchar(80) NOT NULL,
    presentation varchar(120) NOT NULL,
    unit_of_measure varchar(20) NOT NULL DEFAULT 'unidad',
    standard_batch_size integer NOT NULL CHECK (standard_batch_size > 0),
    shelf_life_days integer NULL CHECK (shelf_life_days IS NULL OR shelf_life_days > 0),
    active boolean NOT NULL DEFAULT true,
    created_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS public.work_shifts (
    id serial4 PRIMARY KEY,
    code varchar(20) NOT NULL UNIQUE,
    name varchar(60) NOT NULL,
    start_time time NOT NULL,
    end_time time NOT NULL,
    planned_minutes integer NOT NULL CHECK (planned_minutes > 0),
    active boolean NOT NULL DEFAULT true
);

CREATE TABLE IF NOT EXISTS public.machine_readings (
    id bigserial PRIMARY KEY,
    machine_id integer NOT NULL REFERENCES public.machines(id) ON DELETE CASCADE,
    recorded_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
    usage_hours double precision NOT NULL CHECK (usage_hours >= 0),
    vibration double precision NOT NULL CHECK (vibration >= 0),
    temperature double precision NOT NULL,
    current_amps double precision NOT NULL CHECK (current_amps >= 0),
    rpm double precision NOT NULL CHECK (rpm >= 0),
    pressure double precision NOT NULL CHECK (pressure >= 0),
    failure_probability double precision NOT NULL CHECK (failure_probability BETWEEN 0 AND 100),
    health_status varchar(20) NOT NULL CHECK (health_status IN ('healthy','warning','critical')),
    explanation varchar(500) NOT NULL,
    CONSTRAINT uq_machine_reading_time UNIQUE (machine_id, recorded_at)
);
CREATE INDEX IF NOT EXISTS ix_machine_readings_machine_time ON public.machine_readings (machine_id, recorded_at DESC);
CREATE INDEX IF NOT EXISTS ix_machine_readings_health_status ON public.machine_readings (health_status);

CREATE TABLE IF NOT EXISTS public.product_routings (
    id serial4 PRIMARY KEY,
    product_id integer NOT NULL REFERENCES public.products(id) ON DELETE CASCADE,
    sequence integer NOT NULL CHECK (sequence > 0),
    operation_code varchar(40) NOT NULL,
    operation_name varchar(120) NOT NULL,
    machine_id integer NOT NULL REFERENCES public.machines(id),
    ideal_cycle_time_seconds double precision NOT NULL CHECK (ideal_cycle_time_seconds > 0),
    setup_minutes integer NOT NULL CHECK (setup_minutes >= 0),
    CONSTRAINT uq_product_routing_sequence UNIQUE (product_id, sequence)
);
CREATE INDEX IF NOT EXISTS ix_product_routings_machine_id ON public.product_routings (machine_id);

CREATE TABLE IF NOT EXISTS public.production_orders (
    id serial4 PRIMARY KEY,
    order_number varchar(40) NOT NULL UNIQUE,
    product_id integer NOT NULL REFERENCES public.products(id),
    planned_quantity integer NOT NULL CHECK (planned_quantity > 0),
    planned_start timestamptz NOT NULL,
    planned_end timestamptz NOT NULL,
    status varchar(30) NOT NULL CHECK (status IN ('planned','released','in_progress','completed','cancelled')),
    priority varchar(20) NOT NULL CHECK (priority IN ('low','normal','high','critical')),
    created_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CHECK (planned_end > planned_start)
);
CREATE INDEX IF NOT EXISTS ix_production_orders_status ON public.production_orders (status);

CREATE TABLE IF NOT EXISTS public.production_batches (
    id serial4 PRIMARY KEY,
    batch_number varchar(50) NOT NULL UNIQUE,
    production_order_id integer NOT NULL REFERENCES public.production_orders(id) ON DELETE CASCADE,
    planned_quantity integer NOT NULL CHECK (planned_quantity > 0),
    actual_quantity integer NOT NULL DEFAULT 0 CHECK (actual_quantity >= 0),
    started_at timestamptz NULL,
    completed_at timestamptz NULL,
    status varchar(30) NOT NULL CHECK (status IN ('planned','in_progress','quality_hold','released','completed','rejected')),
    expiry_date date NULL
);
CREATE INDEX IF NOT EXISTS ix_production_batches_order ON public.production_batches (production_order_id);
CREATE INDEX IF NOT EXISTS ix_production_batches_status ON public.production_batches (status);

CREATE TABLE IF NOT EXISTS public.production_runs (
    id serial4 PRIMARY KEY,
    production_order_id integer NOT NULL REFERENCES public.production_orders(id),
    batch_id integer NOT NULL REFERENCES public.production_batches(id),
    product_id integer NOT NULL REFERENCES public.products(id),
    machine_id integer NOT NULL REFERENCES public.machines(id),
    shift_id integer NOT NULL REFERENCES public.work_shifts(id),
    operation_sequence integer NOT NULL CHECK (operation_sequence > 0),
    started_at timestamptz NOT NULL,
    ended_at timestamptz NULL,
    planned_minutes integer NOT NULL CHECK (planned_minutes > 0),
    ideal_cycle_time_seconds double precision NOT NULL CHECK (ideal_cycle_time_seconds > 0),
    status varchar(30) NOT NULL CHECK (status IN ('planned','running','paused','completed','cancelled'))
);
CREATE INDEX IF NOT EXISTS ix_production_runs_machine_time ON public.production_runs (machine_id, started_at DESC);
CREATE INDEX IF NOT EXISTS ix_production_runs_order ON public.production_runs (production_order_id);

CREATE TABLE IF NOT EXISTS public.machine_downtime_events (
    id bigserial PRIMARY KEY,
    production_run_id integer NOT NULL REFERENCES public.production_runs(id) ON DELETE CASCADE,
    machine_id integer NOT NULL REFERENCES public.machines(id),
    started_at timestamptz NOT NULL,
    ended_at timestamptz NULL,
    duration_minutes double precision NOT NULL CHECK (duration_minutes >= 0),
    reason_code varchar(40) NOT NULL,
    reason_description varchar(180) NOT NULL,
    category varchar(60) NOT NULL,
    is_planned boolean NOT NULL DEFAULT false
);
CREATE INDEX IF NOT EXISTS ix_downtime_machine_time ON public.machine_downtime_events (machine_id, started_at DESC);
CREATE INDEX IF NOT EXISTS ix_downtime_reason ON public.machine_downtime_events (reason_code);

CREATE TABLE IF NOT EXISTS public.production_counters (
    id bigserial PRIMARY KEY,
    production_run_id integer NOT NULL REFERENCES public.production_runs(id) ON DELETE CASCADE,
    recorded_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
    total_units integer NOT NULL CHECK (total_units >= 0),
    good_units integer NOT NULL CHECK (good_units >= 0),
    rejected_units integer NOT NULL CHECK (rejected_units >= 0),
    rework_units integer NOT NULL CHECK (rework_units >= 0),
    CHECK (good_units + rejected_units <= total_units)
);
CREATE INDEX IF NOT EXISTS ix_production_counters_run_time ON public.production_counters (production_run_id, recorded_at DESC);

CREATE TABLE IF NOT EXISTS public.oee_results (
    id bigserial PRIMARY KEY,
    production_run_id integer NOT NULL UNIQUE REFERENCES public.production_runs(id) ON DELETE CASCADE,
    calculated_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
    availability double precision NOT NULL CHECK (availability BETWEEN 0 AND 100),
    performance double precision NOT NULL CHECK (performance BETWEEN 0 AND 100),
    quality double precision NOT NULL CHECK (quality BETWEEN 0 AND 100),
    oee double precision NOT NULL CHECK (oee BETWEEN 0 AND 100),
    operating_minutes double precision NOT NULL CHECK (operating_minutes >= 0),
    downtime_minutes double precision NOT NULL CHECK (downtime_minutes >= 0),
    total_units integer NOT NULL CHECK (total_units >= 0),
    good_units integer NOT NULL CHECK (good_units >= 0)
);
