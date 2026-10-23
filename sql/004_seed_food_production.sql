INSERT INTO public.work_shifts (code, name, start_time, end_time, planned_minutes) VALUES
('A','Turno A','06:00','14:00',480),('B','Turno B','14:00','22:00',480),('C','Turno C','22:00','06:00',480)
ON CONFLICT (code) DO NOTHING;

INSERT INTO public.machines (code,name,machine_type,area,max_usage_hours,max_vibration,max_temperature,rated_current,nominal_rpm,max_pressure) VALUES
('RM-101','Transportador de recepción','Transportador','Recepción',10000,7.1,85,35,960,3.5),
('WS-110','Lavadora rotativa','Lavadora','Lavado',10000,7.1,90,40,1200,4.0),
('CR-120','Triturador industrial','Triturador','Preparación',10000,7.1,95,55,1450,4.0),
('MX-130','Mezclador de alto corte','Mezclador','Mezcla',10000,7.1,95,50,1450,4.5),
('PS-140','Pasteurizador tubular','Pasteurizador','Proceso térmico',12000,6.5,110,45,960,6.0),
('HM-150','Homogeneizador','Homogeneizador','Homogeneización',12000,7.1,100,60,1750,8.0),
('TK-160','Tanque de proceso','Tanque','Almacenamiento',15000,5.0,90,25,720,4.0),
('PU-170','Bomba sanitaria','Bomba','Transferencia',10000,7.1,95,40,1750,6.0),
('FL-210','Llenadora rotativa','Llenadora','Llenado',10000,7.1,90,55,1450,5.0),
('CP-220','Taponadora','Taponadora','Tapado',10000,7.1,85,35,1200,4.0),
('LB-230','Etiquetadora','Etiquetadora','Etiquetado',9000,6.5,80,25,960,3.5),
('PK-240','Empacadora flow-pack','Empacadora','Empaque',10000,7.1,90,45,1450,5.0),
('CS-250','Encajonadora automática','Encajonadora','Encajado',10000,7.1,85,40,1200,4.0),
('PL-260','Paletizador robotizado','Robot','Paletizado',12000,6.5,85,50,960,5.0),
('CV-310','Banda transportadora','Transportador','Transporte',10000,7.1,80,30,960,3.0),
('AC-320','Compresor de aire','Compresor','Servicios',12000,7.1,105,65,1750,10.0),
('CH-330','Chiller de proceso','Chiller','Refrigeración',12000,6.5,95,55,1450,8.0),
('BL-340','Caldera de vapor','Caldera','Servicios',15000,6.5,120,60,1450,12.0),
('CIP-350','Sistema CIP','Sistema CIP','Limpieza',12000,6.5,105,50,1450,7.0),
('EX-360','Extractor de aire','Extractor','Extracción',9000,7.1,90,35,1450,3.0)
ON CONFLICT (code) DO UPDATE SET name=EXCLUDED.name,machine_type=EXCLUDED.machine_type,area=EXCLUDED.area;

INSERT INTO public.products (code,name,product_type,presentation,unit_of_measure,standard_batch_size,shelf_life_days) VALUES
('BFP-1L','Bebida de fruta PET 1 L','Bebida','Botella PET 1 L','unidad',48000,180),
('JUG-500','Jugo pasteurizado 500 ml','Jugo','Botella PET 500 ml','unidad',60000,120),
('ISO-600','Bebida isotónica 600 ml','Bebida funcional','Botella PET 600 ml','unidad',55000,240)
ON CONFLICT (code) DO NOTHING;
