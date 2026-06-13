env['res.users'].browse(2).write({'password': 'admin'})
env.cr.commit()
print('Done')
