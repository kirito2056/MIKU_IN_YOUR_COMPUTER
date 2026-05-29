-- 개발용 시드 (선택). 010_indexes IVFFlat lists 튜닝용 최소 1행 포함 가능.

INSERT INTO users (id, display_name, device_id)
VALUES (
    '00000000-0000-4000-8000-000000000001',
    'Master',
    'dev-local'
)
ON CONFLICT (device_id) DO NOTHING;

INSERT INTO growth_stats (user_id)
VALUES ('00000000-0000-4000-8000-000000000001')
ON CONFLICT (user_id) DO NOTHING;
