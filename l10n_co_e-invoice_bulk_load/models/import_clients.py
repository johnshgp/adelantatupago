# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import ValidationError
import base64
import csv
from datetime import date as dt



class ImportClients(models.Model):
    _name = 'import.clients'
    _description = 'import.clients'

    def btn_process(self):
        _procesados = ""
        _procesados_stock = ""
        _noprocesados = ""
        vals={}    
        self.ensure_one()
        if not self.client_match:
            raise ValidationError('Debe seleccionar metodo de busqueda de clientes')
        if not self.delimiter:
            raise ValidationError('Debe ingresar el delimitador')
        if not self.client_file:
            raise ValidationError('Debe seleccionar el archivo')
        if self.state != 'draft':
            raise ValidationError('Archivo procesado!')
        self.file_content = base64.decodebytes(self.client_file)
        lines = self.file_content.split('\n')
        for i,line in enumerate(lines):
            if self.skip_first_line and i == 0:
                continue
            lista = line.split(self.delimiter)
            if len(lista) > 17:
                is_company = lista[0]
                personType = lista[1]
                l10n_latam_identification_type_id = lista[2]
                vat_client = lista[3]
                nombres_client = lista[4]
                apellidos_client = lista[5]
                razon_social = lista[6]
                calle = lista[7]
                estado_client = lista[8]
                ciudad_client = lista[9]
                email_client = lista[10]
                cp_client = lista[11]
                pais_client = lista[12]
                rfiscal = lista[13]
                cuenta_por_cobrar = lista[14]
                tributos = lista[15]
                telefono = lista[16]
                mobil = lista[17]

                vals.clear()

                # Carga vals
                client = self.env['res.partner'].search([(self.client_match,'=',vat_client)])
                if not client:
                    
                    # Carga vals
                    if is_company != '': 
                        if is_company == 'Compania' or is_company == 'Compañia' or is_company == 'Compañía':
                            vals['is_company'] = True
                        elif is_company == 'Usuario':
                            vals['is_company'] = False
                        else:
                            raise ValidationError("El CSV no se procesara por estar mal formado en la linea {0}, la primera columna que refiere a el tipo de cliete tiene que ser Compania o Usuario, contenido de linea: {1}".format(i, line))
                    if personType != '':  
                        if personType == 'Juridica' or personType == 'Jurídica':
                            vals['personType'] = '2'
                        elif personType == 'Natural':
                            vals['personType'] = '1'
                        else:
                            raise ValidationError("El CSV no se procesara por estar mal formado en la linea {0}, la columna Tipo de Persona tiene que ser Juridica o Natural, contenido de linea: {1}".format(i, line))
                    if vat_client != '': 
                        characters = "."
                        for x in range(len(characters)):
                            vat_client = vat_client.replace(characters[x],"")
                        if len(vat_client.split('-',2))>1:
                             vat_client = vat_client.split('-',2)[0]
                        vals['vat'] = vat_client
                    if email_client != '': vals['email'] = email_client
                    else:
                        raise ValidationError("El CSV no se procesara por falta de email en la linea {0}, contenido de linea: {1}".format(i, line))
                    if nombres_client != '': 
                        vals['x_name1'] = nombres_client.split(' ',2)[0]
                        if len(nombres_client.split(' ',2)) > 1:
                            _snombre = nombres_client.split(' ',2)[1]
                            if _snombre != '':
                                vals['x_name2'] = _snombre
                        if apellidos_client != '':     
                            vals['name'] = nombres_client + ' ' + apellidos_client
                        else:
                            vals['name'] = nombres_client
                    elif not is_company == 'Compania' and not is_company == 'Compañia' and not is_company == 'Compañía':
                        raise ValidationError("El CSV no se procesara porque es necesario el primer nombre en la linea {0}, contenido de linea: {1}".format(i, line))

                    if apellidos_client != '': 
                        vals['x_lastname1'] = apellidos_client.split(' ',2)[0]
                        if len(apellidos_client.split(' ',2)) > 1:
                            _sapellido = apellidos_client.split(' ',2)[1]
                            if _sapellido != '':
                                vals['x_lastname2'] = _sapellido
                    elif not is_company == 'Compania' and not is_company == 'Compañia' and not is_company == 'Compañía':
                        raise ValidationError("El CSV no se procesara porque es necesario el primer apellido en la linea {0}, contenido de linea: {1}".format(i, line))
                    if razon_social != '': 
                        vals['companyName'] = razon_social
                        vals['name'] = razon_social
                    elif is_company == 'Compania' or is_company == 'Compañia' or is_company == 'Compañía':
                        raise ValidationError("El CSV no se procesara porque es necesario una razon social en la linea {0}, contenido de linea: {1}".format(i, line))

                    if calle != '': vals['street'] = calle
                    else:
                        raise ValidationError("El CSV no se procesara porque es necesario una direccion en la linea {0}, contenido de linea: {1}".format(i, line))
                    
                    # Seleccion de pais
                    if pais_client != '': 
                        tmp_pais_id = 0
                        tmp_pais_id = self.env['res.country'].search([('name','=ilike',pais_client)]).id
                        if tmp_pais_id != 0: vals['country_id'] = tmp_pais_id
                        else:
                            raise ValidationError("El CSV no se procesara por que no se encuentra el pais {0} en la linea {1}, contenido de linea: {2}".format(pais_client, i, line))
                        if tmp_pais_id != 0 and estado_client != '':
                            tmp_estado_id = 0
                            tmp_estado_id = self.env['res.country.state'].search([('name','=ilike',estado_client)]).id
                            if tmp_estado_id != 0: vals['state_id'] = tmp_estado_id
                            else:
                                raise ValidationError("El CSV no se procesara por que no se encuentra el estado {0} en la linea {1}, contenido de linea: {2}".format(estado_client, i, line))
                            if tmp_estado_id != 0 and ciudad_client != '':
                                tmp_ciudad_id = 0
                                tmp_ciudad_id = self.env['res.country.state.city'].search([('name','=ilike',ciudad_client)]).id
                                if tmp_ciudad_id != 0: vals['xcity'] = tmp_ciudad_id
                                else:
                                    raise ValidationError("El CSV no se procesara por que no se encuentra la ciudad {0} en la linea {1}, contenido de linea: {2}".format(ciudad_client, i, line))
                            
                    if cp_client != '': 
                        vals['zip'] = cp_client
                    # Seleccion de Tipo de Identificacion
                    if l10n_latam_identification_type_id != '': 
                        tmp_identification_id = 0
                        if l10n_latam_identification_type_id == 'SI':
                            tmp_identification_id = self.env['l10n_latam.identification.type'].search([('name','=','Sin Identificación')]).id
                        elif l10n_latam_identification_type_id == 'NIT':
                            tmp_identification_id = self.env['l10n_latam.identification.type'].search([('name','=','NIT')]).id
                        elif l10n_latam_identification_type_id == 'CC':
                            tmp_identification_id = self.env['l10n_latam.identification.type'].search([('name','=','Cédula de ciudadanía')]).id
                        elif l10n_latam_identification_type_id == 'RC':
                            tmp_identification_id = self.env['l10n_latam.identification.type'].search([('name','=','Registro Civil')]).id
                        elif l10n_latam_identification_type_id == 'TE':
                            tmp_identification_id = self.env['l10n_latam.identification.type'].search([('name','=','Tarjeta de extranjería')]).id
                        elif l10n_latam_identification_type_id == 'TI':
                            tmp_identification_id = self.env['l10n_latam.identification.type'].search([('name','=','Tarjeta de Identidad')]).id
                        elif l10n_latam_identification_type_id == 'CE':
                            tmp_identification_id = self.env['l10n_latam.identification.type'].search([('name','=','Cédula de extranjería')]).id
                        elif l10n_latam_identification_type_id == 'CD':
                            tmp_identification_id = self.env['l10n_latam.identification.type'].search([('name','=','Carné Diplomatico')]).id
                        elif l10n_latam_identification_type_id == 'SP':
                            tmp_identification_id = self.env['l10n_latam.identification.type'].search([('name','=','Salvoconducto de Permanencia')]).id
                        elif l10n_latam_identification_type_id == 'NIUP':
                            tmp_identification_id = self.env['l10n_latam.identification.type'].search([('name','=','NIUP')]).id
                        elif l10n_latam_identification_type_id == 'IC':
                            tmp_identification_id = self.env['l10n_latam.identification.type'].search([('name','=','INACTIVO - Cédula')]).id
                        elif l10n_latam_identification_type_id == 'PA':
                            tmp_identification_id = self.env['l10n_latam.identification.type'].search([('name','=','Pasaporte')]).id
                        else:
                            raise ValidationError("El CSV no se procesara por que no se encuentra el tipo de identificacion {0} en la linea {1}, contenido de linea: {2}".format(l10n_latam_identification_type_id, i, line))

                        if tmp_identification_id != 0: vals['l10n_latam_identification_type_id'] = tmp_identification_id
                    
                    # Seleccion de Responsabilidad Fiscal
                    if rfiscal != '':
                        tmp_fiscal_id = 0
                        if rfiscal == 'O-13':
                            tmp_fiscal_id = self.env['dian.fiscal.responsability'].search([('name','=ilike', 'Gran contribuyente')]).id
                        elif rfiscal == 'O-15':
                            tmp_fiscal_id = self.env['dian.fiscal.responsability'].search([('name','=ilike', 'Autorretenedor')]).id
                        elif rfiscal == 'O-23':
                            tmp_fiscal_id = self.env['dian.fiscal.responsability'].search([('name','=ilike', 'Agente de retención IVA')]).id
                        elif rfiscal == 'O-47':
                            tmp_fiscal_id = self.env['dian.fiscal.responsability'].search([('name','=ilike', 'Régimen Simple de Tributación')]).id
                        elif rfiscal == 'R-99-PN':
                            tmp_fiscal_id = self.env['dian.fiscal.responsability'].search([('name','=ilike', 'No responsable')]).id
                        else:
                            raise ValidationError("El CSV no se procesara por que no se encuentra Responsabilidad Fiscal {0} en la linea {1}, contenido de linea: {2}".format(rfiscal, i, line))

                        if tmp_fiscal_id != 0: vals['fiscal_responsability_ids'] = [(4,tmp_fiscal_id)]

                    if cuenta_por_cobrar != '':
                        ccobrar_id = self.env['account.account'].search([('code','=', cuenta_por_cobrar)]).id
                        if ccobrar_id:
                            vals['property_account_receivable_id'] = ccobrar_id
                        else:
                            raise ValidationError("El CSV no se procesara por que no se encuentra Cuenta por Cobrar {0} en la linea {1}, contenido de linea: {2}".format(cuenta_por_cobrar, i, line))
                    else:
                        raise ValidationError("El CSV no se procesara por que no se encuentra Cuenta por Cobrar {0} en la linea {1}, contenido de linea: {2}".format(cuenta_por_cobrar, i, line))

                            

                    # Seleccion de Tributo
                    if tributos != '':
                        tmp_tributos_id = 0
                        if tributos == '01':
                            tmp_tributos_id = self.env['dian.tributes'].search([('name','=ilike', 'IVA')]).id
                        if tributos == '04':
                            tmp_tributos_id = self.env['dian.tributes'].search([('name','=ilike', 'INC')]).id
                        if tributos == 'ZA':
                            tmp_tributos_id = self.env['dian.tributes'].search([('name','=ilike', 'IVA e INC')]).id
                        if tributos == 'ZZ':
                            tmp_tributos_id = self.env['dian.tributes'].search([('name','=ilike', 'No Aplica')]).id
                            
                        
                        if tmp_tributos_id != 0: vals['tribute_id'] = tmp_tributos_id

                    if telefono != '': vals['phone'] = telefono
                    if mobil != '': vals['mobile'] = mobil
                    self.env['res.partner'].sudo().create(vals)
                    _procesados += "{} \n".format(vat_client)
                else:
                    _noprocesados += "{} \n".format(vat_client)
            else:
                raise ValidationError("El CSV no se procesara por estar mal formado en la linea {0}, contenido de linea: {1}. Se necesitan al menos 18 columnas".format(i, line))
        self.clientes_creados = _procesados
        self.not_processed_content = _noprocesados
        self.state = 'processed'

    name = fields.Char('Nombre')
    client_file = fields.Binary('Archivo')
    delimiter = fields.Char('Delimitador',default=";")
    state = fields.Selection(selection=[('draft','Borrador'),('processed','Procesado')],string='Estado',default='draft')
    file_content = fields.Text('Texto archivo')
    not_processed_content = fields.Text('Texto no procesado')
    clientes_creados = fields.Text('Productos Creados')
    skip_first_line = fields.Boolean('Saltear primera linea',default=True)
    client_match = fields.Selection(selection=[('vat','Vat')],string='Buscar clientes por...',default='vat')

	
