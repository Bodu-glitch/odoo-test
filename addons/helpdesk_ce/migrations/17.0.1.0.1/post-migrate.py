def migrate(cr, version):
    """Assign the first available stage to tickets that have no stage."""
    cr.execute("SELECT id FROM helpdesk_stage ORDER BY sequence, id LIMIT 1")
    row = cr.fetchone()
    if row:
        stage_id = row[0]
        cr.execute(
            "UPDATE helpdesk_ticket SET stage_id = %s WHERE stage_id IS NULL",
            (stage_id,),
        )
