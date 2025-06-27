"""
Ofi Documentos, vistas
"""

from datetime import datetime
import json

from flask import Blueprint, current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from lib.datatables import get_datatable_parameters, output_datatable_json
from lib.folio import validar_folio
from lib.safe_string import safe_string, safe_message, safe_clave, safe_uuid
from hercules.blueprints.bitacoras.models import Bitacora
from hercules.blueprints.modulos.models import Modulo
from hercules.blueprints.permisos.models import Permiso
from hercules.blueprints.usuarios.decorators import permission_required
from hercules.blueprints.ofi_documentos.models import OfiDocumento
from hercules.blueprints.ofi_documentos.forms import OfiDocumentoNewForm, OfiDocumentoEditForm, OfiDocumentoSignForm
from hercules.blueprints.ofi_plantillas.models import OfiPlantilla
from hercules.blueprints.usuarios.models import Usuario
from hercules.blueprints.autoridades.models import Autoridad
from hercules.blueprints.ofi_documentos_destinatarios.models import OfiDocumentoDestinatario

# Roles
ROL_ESCRITOR = "OFICIOS ESCRITOR"
ROL_FIRMANTE = "OFICIOS FIRMANTE"
ROL_LECTOR = "OFICIOS LECTOR"

# Constantes para fecha de vencimiento de oficios
DIAS_VENCIMIENTO_ADVERTENCIA = -3
DIAS_VENCIMIENTO_EMERGENCIA = -1

MODULO = "OFI DOCUMENTOS"

ofi_documentos = Blueprint("ofi_documentos", __name__, template_folder="templates")


@ofi_documentos.before_request
@login_required
@permission_required(MODULO, Permiso.VER)
def before_request():
    """Permiso por defecto"""


@ofi_documentos.route("/ofi_documentos/datatable_json", methods=["GET", "POST"])
def datatable_json():
    """DataTable JSON para listado de Ofi Documentos"""
    # Tomar parámetros de Datatables
    draw, start, rows_per_page = get_datatable_parameters()
    # Consultar
    consulta = OfiDocumento.query
    # Primero filtrar por columnas propias
    if "estatus" in request.form:
        consulta = consulta.filter(OfiDocumento.estatus == request.form["estatus"])
    else:
        consulta = consulta.filter(OfiDocumento.estatus == "A")
    if "usuario_id" in request.form:
        consulta = consulta.filter(OfiDocumento.usuario_id == request.form["usuario_id"])
    if "estado" in request.form:
        consulta = consulta.filter(OfiDocumento.estado == request.form["estado"])
    if "folio" in request.form:
        folio = request.form["folio"]
        consulta = consulta.filter(OfiDocumento.folio.contains(folio))
    if "descripcion" in request.form:
        descripcion = safe_string(request.form["descripcion"])
        if descripcion:
            consulta = consulta.filter(OfiDocumento.descripcion.contains(descripcion))
    # Luego filtrar por columnas de otras tablas
    tabla_usuario_incluida = False
    if "autor" in request.form:
        if tabla_usuario_incluida is False:
            consulta = consulta.join(Usuario)
            tabla_usuario_incluida = True
        autor = request.form["autor"].lower()
        consulta = consulta.filter(Usuario.email.contains(autor))
    if "autoridad" in request.form:
        autoridad = safe_clave(request.form["autoridad"])
        if autoridad:
            if tabla_usuario_incluida is False:
                consulta = consulta.join(Usuario)
                tabla_usuario_incluida = True
            consulta = consulta.join(Autoridad, Usuario.autoridad_id == Autoridad.id)
            consulta = consulta.filter(Autoridad.clave.contains(autoridad))
    if "usuario_autoridad_id" in request.form:
        if tabla_usuario_incluida is False:
            consulta = consulta.join(Usuario)
            tabla_usuario_incluida = True
        consulta = consulta.filter(Usuario.autoridad_id == request.form["usuario_autoridad_id"])
    if "usuario_destinatario_id" in request.form:
        consulta = consulta.join(OfiDocumentoDestinatario, OfiDocumentoDestinatario.ofi_documento_id == OfiDocumento.id)
        consulta = consulta.filter(OfiDocumentoDestinatario.usuario_id == request.form["usuario_destinatario_id"])
        consulta = consulta.filter(OfiDocumentoDestinatario.estatus == "A")
    # Ordenar y paginar
    registros = consulta.order_by(OfiDocumento.creado.desc()).offset(start).limit(rows_per_page).all()
    total = consulta.count()
    # Elaborar datos para DataTable
    data = []
    for resultado in registros:
        # Formar campo de vencimiento
        vencimiento_fecha = resultado.vencimiento_fecha.strftime("%Y-%m-%d") if resultado.vencimiento_fecha else "-"
        vencimiento_icono = ""
        dias_vencimiento = ""
        if resultado.vencimiento_fecha is not None:
            dias_vencimiento = (datetime.now().date() - resultado.vencimiento_fecha).days
            if DIAS_VENCIMIENTO_EMERGENCIA <= dias_vencimiento <= 0:
                vencimiento_icono = "🚨"
            if DIAS_VENCIMIENTO_ADVERTENCIA <= dias_vencimiento < DIAS_VENCIMIENTO_EMERGENCIA:
                vencimiento_icono = "⚠️"
        vencimiento = f"{vencimiento_fecha} {vencimiento_icono}"
        # Elaborar registro
        data.append(
            {
                "detalle": {
                    "id": resultado.id,
                    "url": url_for("ofi_documentos.detail", ofi_documento_id=resultado.id),
                },
                "autor": {
                    "email": resultado.usuario.email,
                    "nombre": resultado.usuario.nombre,
                    "url": url_for("usuarios.detail", usuario_id=resultado.usuario.id),
                },
                "autoridad": {
                    "clave": resultado.usuario.autoridad.clave,
                    "nombre": resultado.usuario.autoridad.descripcion_corta,
                    "url": (
                        url_for("autoridades.detail", autoridad_id=resultado.usuario.autoridad.id)
                        if current_user.can_view("AUTORIDADES")
                        else ""
                    ),
                },
                "folio": resultado.folio,
                "vencimiento": vencimiento,
                "descripcion": resultado.descripcion,
                "creado": resultado.creado.strftime("%Y-%m-%d %H:%M"),
                "estado": resultado.estado,
                "iconos": {
                    "archivado": resultado.esta_archivado,
                    "cancelado": resultado.esta_cancelado,
                },
            }
        )
    # Entregar JSON
    return output_datatable_json(draw, total, data)


@ofi_documentos.route("/ofi_documentos")
def list_active():
    """Listado de Ofi Documentos activos"""
    return list_active_mi_bandeja_entrada()


@ofi_documentos.route("/ofi_documentos/mis_oficios")
def list_active_mis_oficios():
    """Listado de Ofi Documentos Mis Oficios"""
    # Mostrar botones según el rol
    mostrar_boton_nuevo = False
    roles = current_user.get_roles()
    if ROL_FIRMANTE in roles or ROL_ESCRITOR in roles:
        mostrar_boton_nuevo = True
    # Si no se cuenta con los roles de FIRMANTE o ESCRITOR reenviarlo a vista de Bandeja de Entrada
    if ROL_FIRMANTE not in roles and ROL_ESCRITOR not in roles:
        return redirect(url_for("ofi_documentos.list_active_mi_bandeja_entrada"))
    # Entregar
    return render_template(
        "ofi_documentos/list.jinja2",
        filtros=json.dumps({"estatus": "A", "usuario_id": current_user.id}),
        titulo="Mis Oficios",
        estatus="A",
        estados=OfiDocumento.ESTADOS,
        mostrar_boton_nuevo=mostrar_boton_nuevo,
    )


@ofi_documentos.route("/ofi_documentos/mi_bandeja_entrada")
def list_active_mi_bandeja_entrada():
    """Listado de Ofi Documentos Mi Bandeja de Entrada"""
    # Mostrar botones según el rol
    mostrar_boton_nuevo = False
    roles = current_user.get_roles()
    if ROL_FIRMANTE in roles or ROL_ESCRITOR in roles:
        mostrar_boton_nuevo = True
    # Entregar
    return render_template(
        "ofi_documentos/list.jinja2",
        filtros=json.dumps({"estatus": "A", "estado": "ENVIADO", "usuario_destinatario_id": current_user.id}),
        titulo="Mi Bandeja de Entrada",
        estatus="A",
        estados=OfiDocumento.ESTADOS,
        mostrar_boton_nuevo=mostrar_boton_nuevo,
    )


@ofi_documentos.route("/ofi_documentos/mi_autoridad")
def list_active_mi_autoridad():
    """Listado de Ofi Documentos de la autoridad del usuario"""
    # Mostrar botones según el rol
    mostrar_boton_nuevo = False
    roles = current_user.get_roles()
    if ROL_FIRMANTE in roles or ROL_ESCRITOR in roles:
        mostrar_boton_nuevo = True
    # Entregar
    return render_template(
        "ofi_documentos/list.jinja2",
        filtros=json.dumps({"estatus": "A", "usuario_autoridad_id": current_user.autoridad.id}),
        titulo="Mi Autoridad",
        estatus="A",
        estados=OfiDocumento.ESTADOS,
        mostrar_boton_nuevo=mostrar_boton_nuevo,
    )


@ofi_documentos.route("/ofi_documentos/eliminados")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def list_inactive():
    """Listado de Ofi Documentos eliminados"""
    return render_template(
        "ofi_documentos/list.jinja2",
        filtros=json.dumps({"estatus": "B"}),
        titulo="Oficios eliminados",
        estatus="B",
        estados=OfiDocumento.ESTADOS,
    )


@ofi_documentos.route("/ofi_documentos/<ofi_documento_id>")
def detail(ofi_documento_id):
    """Detalle de un Ofi Documento"""
    # Consultar el oficio
    ofi_documento_id = safe_uuid(ofi_documento_id)
    if not ofi_documento_id:
        flash("ID de oficio inválido", "warning")
        return redirect(url_for("ofi_documentos.list_active"))
    ofi_documento = OfiDocumento.query.get_or_404(ofi_documento_id)
    # Validar que si es BORRADOR o FIRMADO se debe tener el rol ESCRITOR o FIRMANTE para verlo
    # En cambio, si fue ENVIADO, ARCHIVADO o CANCELADO si debe de verse
    roles = current_user.get_roles()
    if (
        (ofi_documento.estado == "BORRADOR" or ofi_documento.estado == "FIRMADO")
        and ROL_ESCRITOR not in roles
        and ROL_FIRMANTE not in roles
    ):
        flash("Se necesitan roles de ESCRITOR o FIRMANTE para ver un oficio en estado BORRADOR o FIRMADO", "warning")
        return redirect(url_for("ofi_documentos.list_active"))
    # Si el oficio está eliminado y NO es administrador, mostrar mensaje y redirigir
    if ofi_documento.estatus != "A" and current_user.can_admin(MODULO) is False:
        flash("El oficio está eliminado", "warning")
        return redirect(url_for("ofi_documentos.list_active"))
    # Consultar el usuario firmante, si lo tiene
    usuario_firmante = None
    if ofi_documento.firma_simple_usuario_id is not None:
        usuario_firmante = Usuario.query.get(ofi_documento.firma_simple_usuario_id)
    # Si el usuario que lo ve es un destinatario, se va a marcar como leído
    mostrar_boton_responder = False
    if ofi_documento.estado == "ENVIADO":
        # Buscar al usuario entre los destinatarios
        usuario_destinatario = (
            OfiDocumentoDestinatario.query.filter_by(ofi_documento_id=ofi_documento.id)
            .filter_by(usuario_id=current_user.id)
            .first()
        )
        # Marcar como leído si es que no lo ha sido
        if usuario_destinatario is not None and usuario_destinatario.fue_leido is False:
            usuario_destinatario.fue_leido = True
            usuario_destinatario.fue_leido_tiempo = datetime.now()
            usuario_destinatario.save()
        if usuario_destinatario is not None:
            mostrar_boton_responder = True
    # Mostrar botones según el rol
    mostrar_boton_otras_categorias = True
    mostrar_boton_firmar = False
    mostrar_boton_editar = True
    roles = current_user.get_roles()
    if ROL_FIRMANTE in roles:
        mostrar_boton_firmar = True
    if ROL_ESCRITOR not in roles and ROL_FIRMANTE not in roles:
        mostrar_boton_editar = False
        mostrar_boton_responder = False
        mostrar_boton_otras_categorias = False
    # Mostrar botón de Archivar cuando se envía, no esta archivado y es el usuario creador
    mostrar_boton_archivar = False
    if (
        ofi_documento.estado == "ENVIADO"
        and ofi_documento.esta_archivado is False
        and ofi_documento.usuario_id == current_user.id
    ):
        mostrar_boton_archivar = True
    # Mostrar el botón de descancelar solo al firmante si ya está firmado
    mostrar_boton_descancelar = False
    mostrar_boton_desarchivar = False
    if ofi_documento.estado == "BORRADOR" and ofi_documento.usuario_id == current_user.id:
        mostrar_boton_descancelar = True
        mostrar_boton_desarchivar = True
    if ofi_documento.estado == "BORRADOR" and ROL_FIRMANTE in roles:
        mostrar_boton_descancelar = True
        mostrar_boton_desarchivar = True
    if ofi_documento.estado == "FIRMADO" and ROL_FIRMANTE in roles:
        mostrar_boton_descancelar = True
        mostrar_boton_desarchivar = True
    if ofi_documento.estado == "ENVIADO" and ROL_FIRMANTE in roles:
        mostrar_boton_desarchivar = True
    # Para mostrar el contenido del documento, se usa Syncfusion Document Editor con un formulario que NO se envía
    form = OfiDocumentoNewForm()
    form.descripcion.data = ofi_documento.descripcion
    form.contenido_sfdt.data = ofi_documento.contenido_sfdt
    # Si está definida la variable de entorno SYNCFUSION_LICENSE_KEY
    if current_app.config.get("SYNCFUSION_LICENSE_KEY"):
        # Entregar detail_syncfusion_document.jinja2
        return render_template(
            "ofi_documentos/detail_syncfusion_document.jinja2",
            ofi_documento=ofi_documento,
            usuario_firmante=usuario_firmante,
            form=form,
            mostrar_boton_responder=mostrar_boton_responder,
            mostrar_boton_firmar=mostrar_boton_firmar,
            mostrar_boton_editar=mostrar_boton_editar,
            mostrar_boton_descancelar=mostrar_boton_descancelar,
            mostrar_boton_archivar=mostrar_boton_archivar,
            mostrar_boton_desarchivar=mostrar_boton_desarchivar,
            mostrar_boton_otras_categorias=mostrar_boton_otras_categorias,
            syncfusion_license_key=current_app.config["SYNCFUSION_LICENSE_KEY"],
        )
    # De lo contrario, entregar detail.jinja2
    return render_template(
        "ofi_documentos/detail.jinja2",
        ofi_documento=ofi_documento,
        usuario_firmante=usuario_firmante,
        form=form,
        mostrar_boton_responder=mostrar_boton_responder,
        mostrar_boton_firmar=mostrar_boton_firmar,
        mostrar_boton_editar=mostrar_boton_editar,
        mostrar_boton_descancelar=mostrar_boton_descancelar,
        mostrar_boton_archivar=mostrar_boton_archivar,
        mostrar_boton_desarchivar=mostrar_boton_desarchivar,
        mostrar_boton_otras_categorias=mostrar_boton_otras_categorias,
    )


@ofi_documentos.route("/ofi_documentos/nuevo/<ofi_plantilla_id>", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.CREAR)
def new(ofi_plantilla_id):
    """Nuevo Ofi Documento"""
    # Validar que el usuario tenga el rol ESCRITOR o FIRMANTE, para que un ADMINISTRADOR no pueda crear
    roles = current_user.get_roles()
    if ROL_ESCRITOR not in roles and ROL_FIRMANTE not in roles:
        flash("Se necesitan roles de ESCRITOR o FIRMANTE para crear un oficio", "warning")
        return redirect(url_for("ofi_documentos.list_active"))
    # Consultar la plantilla
    ofi_plantilla_id = safe_uuid(ofi_plantilla_id)
    if not ofi_plantilla_id:
        flash("ID de plantilla inválido", "warning")
        return redirect(url_for("ofi_plantillas.list_active"))
    ofi_plantilla = OfiPlantilla.query.get_or_404(ofi_plantilla_id)
    # Validar que la plantilla no esté eliminada
    if ofi_plantilla.estatus == "B":
        flash("La plantilla está eliminada", "warning")
        return redirect(url_for("ofi_plantillas.list_active"))
    # Validar que la plantilla no esté archivada
    if ofi_plantilla.esta_archivado:
        flash("La plantilla está archivada", "warning")
        return redirect(url_for("ofi_plantillas.list_active"))
    # Obtener el formulario
    form = OfiDocumentoNewForm()
    if form.validate_on_submit():
        es_valido = True
        # Validar el folio, separar el número y el año
        folio = form.folio.data.strip()
        numero_folio = None
        anio_folio = None
        if folio != "":
            try:
                numero_folio, anio_folio = validar_folio(folio)
            except ValueError as error:
                flash(str(error), "warning")
                es_valido = False
        # Validar la fecha de vencimiento
        vencimiento_fecha = form.vencimiento_fecha.data
        if vencimiento_fecha is not None and vencimiento_fecha < datetime.now().date():
            flash("La fecha de vencimiento no puede ser anterior a la fecha actual", "warning")
            es_valido = False
        if es_valido:
            ofi_documento = OfiDocumento(
                usuario=current_user,
                descripcion=safe_string(form.descripcion.data, save_enie=True),
                folio=folio,
                folio_anio=anio_folio,
                folio_num=numero_folio,
                vencimiento_fecha=vencimiento_fecha,
                contenido_md=form.contenido_md.data.strip(),
                contenido_html=form.contenido_html.data.strip(),
                contenido_sfdt=form.contenido_sfdt.data.strip(),
                estado="BORRADOR",
                cadena_oficio_id=form.cadena_oficio_id.data if form.cadena_oficio_id.data else None,
            )
            ofi_documento.save()
            bitacora = Bitacora(
                modulo=Modulo.query.filter_by(nombre=MODULO).first(),
                usuario=current_user,
                descripcion=safe_message(f"Nuevo Oficio Documento {ofi_documento.descripcion}"),
                url=url_for("ofi_documentos.detail", ofi_documento_id=ofi_documento.id),
            )
            bitacora.save()
            flash(bitacora.descripcion, "success")
            return redirect(bitacora.url)
    # Cargar los datos de la plantilla en el formulario
    form.descripcion.data = ofi_plantilla.descripcion
    form.contenido_md.data = ofi_plantilla.contenido_md
    form.contenido_html.data = ofi_plantilla.contenido_html
    form.contenido_sfdt.data = ofi_plantilla.contenido_sfdt
    # Si está definida la variable de entorno SYNCFUSION_LICENSE_KEY
    if current_app.config.get("SYNCFUSION_LICENSE_KEY"):
        # Entregar new_syncfusion_document.jinja2
        return render_template(
            "ofi_documentos/new_syncfusion_document.jinja2",
            form=form,
            ofi_plantilla_id=ofi_plantilla_id,
            syncfusion_license_key=current_app.config["SYNCFUSION_LICENSE_KEY"],
        )
    # De lo contrario, entregar new_ckeditor5.jinja2
    return render_template(
        "ofi_documentos/new_ckeditor5.jinja2",
        form=form,
        ofi_plantilla_id=ofi_plantilla_id,
    )


@ofi_documentos.route("/ofi_documentos/edicion/<ofi_documento_id>", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.MODIFICAR)
def edit(ofi_documento_id):
    """Editar Ofi Documento"""
    # Validar que el usuario tenga el rol ESCRITOR o FIRMANTE, para que un ADMINISTRADOR no pueda editar
    roles = current_user.get_roles()
    if ROL_ESCRITOR not in roles and ROL_FIRMANTE not in roles:
        flash("Se necesitan roles de ESCRITOR o FIRMANTE para editar un oficio", "warning")
        return redirect(url_for("ofi_documentos.list_active"))
    # Consultar el oficio
    ofi_documento_id = safe_uuid(ofi_documento_id)
    if not ofi_documento_id:
        flash("ID de oficio inválido", "warning")
        return redirect(url_for("ofi_documentos.list_active"))
    ofi_documento = OfiDocumento.query.get_or_404(ofi_documento_id)
    # Validar que la autoridad del oficio sea la misma que la del usuario
    if ofi_documento.usuario.autoridad_id != current_user.autoridad_id:
        flash("No tienes permiso para editar este oficio, pertenece a otra autoridad", "warning")
        return redirect(url_for("ofi_documentos.list_active"))
    # Validar que tenga el estado BORRADOR
    if ofi_documento.estado != "BORRADOR":
        flash("El oficio no está en estado BORRADOR, no se puede editar", "warning")
        return redirect(url_for("ofi_documentos.list_active"))
    # Validar que no esté cancelado
    if ofi_documento.esta_cancelado:
        flash("El oficio está cancelado", "warning")
        return redirect(url_for("ofi_documentos.list_active"))
    # Validar que no esté archivado
    if ofi_documento.esta_archivado:
        flash("El oficio está archivado", "warning")
        return redirect(url_for("ofi_documentos.list_active"))
    # Obtener el formulario
    form = OfiDocumentoEditForm()
    if form.validate_on_submit():
        es_valido = True
        # Validar el folio, separar el número y el año
        folio = form.folio.data.strip()
        numero_folio = None
        anio_folio = None
        if folio != "":
            try:
                numero_folio, anio_folio = validar_folio(folio)
            except ValueError as error:
                flash(str(error), "warning")
                es_valido = False
        # Validar la fecha de vencimiento
        vencimiento_fecha = form.vencimiento_fecha.data
        if vencimiento_fecha is not None and vencimiento_fecha < datetime.now().date():
            flash("La fecha de vencimiento no puede ser anterior a la fecha actual", "warning")
            es_valido = False
        if es_valido:
            ofi_documento.descripcion = safe_string(form.descripcion.data, save_enie=True)
            ofi_documento.folio = folio
            ofi_documento.folio_anio = anio_folio
            ofi_documento.folio_num = numero_folio
            ofi_documento.vencimiento_fecha = vencimiento_fecha
            ofi_documento.contenido_md = form.contenido_md.data.strip()
            ofi_documento.contenido_html = form.contenido_html.data.strip()
            ofi_documento.contenido_sfdt = form.contenido_sfdt.data.strip()
            ofi_documento.save()
            bitacora = Bitacora(
                modulo=Modulo.query.filter_by(nombre=MODULO).first(),
                usuario=current_user,
                descripcion=safe_message(f"Editado Oficio Documento {ofi_documento.descripcion}"),
                url=url_for("ofi_documentos.detail", ofi_documento_id=ofi_documento.id),
            )
            bitacora.save()
            flash(bitacora.descripcion, "success")
            return redirect(bitacora.url)
    # Cargar los datos en el formulario
    form.descripcion.data = ofi_documento.descripcion
    form.folio.data = ofi_documento.folio
    form.vencimiento_fecha.data = ofi_documento.vencimiento_fecha
    form.contenido_md.data = ofi_documento.contenido_md
    form.contenido_html.data = ofi_documento.contenido_html
    form.contenido_sfdt.data = ofi_documento.contenido_sfdt
    # Si está definida la variable de entorno SYNCFUSION_LICENSE_KEY
    if current_app.config.get("SYNCFUSION_LICENSE_KEY"):
        # Entregar edit_syncfusion_document.jinja2
        return render_template(
            "ofi_documentos/edit_syncfusion_document.jinja2",
            form=form,
            ofi_documento=ofi_documento,
            syncfusion_license_key=current_app.config["SYNCFUSION_LICENSE_KEY"],
        )
    # De lo contrario, entregar edit_ckeditor5.jinja2
    return render_template(
        "ofi_documentos/edit_ckeditor5.jinja2",
        form=form,
        ofi_documento=ofi_documento,
    )


@ofi_documentos.route("/ofi_documentos/firmar/<ofi_documento_id>", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.MODIFICAR)
def sign(ofi_documento_id):
    """Firmar un Ofi Documento"""
    # Validar que el usuario tenga el rol FIRMANTE, para que un ADMINISTRADOR no pueda firmar
    if ROL_FIRMANTE not in current_user.get_roles():
        flash("Se necesita el rol de FIRMANTE para firmar un oficio", "warning")
        return redirect(url_for("ofi_documentos.list_active"))
    # Consultar el oficio
    ofi_documento_id = safe_uuid(ofi_documento_id)
    if not ofi_documento_id:
        flash("ID de oficio inválido", "warning")
        return redirect(url_for("ofi_documentos.list_active"))
    ofi_documento = OfiDocumento.query.get_or_404(ofi_documento_id)
    # Validar que la autoridad del oficio sea la misma que la del usuario
    if ofi_documento.usuario.autoridad_id != current_user.autoridad_id:
        flash("No tienes permiso para firmar este oficio, pertenece a otra autoridad", "warning")
        return redirect(url_for("ofi_documentos.list_active"))
    # Validar el estatus, que no esté eliminado
    if ofi_documento.estatus != "A":
        flash("El oficio está eliminado", "warning")
        return redirect(url_for("ofi_documentos.detail", ofi_documento_id=ofi_documento.id))
    # Validar que tenga el estado BORRADOR
    if ofi_documento.estado != "BORRADOR":
        flash("El oficio no está en estado BORRADOR, no se puede firmar", "warning")
        return redirect(url_for("ofi_documentos.detail", ofi_documento_id=ofi_documento.id))
    # Validar la fecha de vencimiento
    if ofi_documento.vencimiento_fecha is not None and ofi_documento.vencimiento_fecha < datetime.now().date():
        flash("La fecha de vencimiento no puede ser anterior a la fecha actual", "warning")
        return redirect(url_for("ofi_documentos.detail", ofi_documento_id=ofi_documento.id))
    # Obtener el formuario
    form = OfiDocumentoSignForm()
    if form.validate_on_submit():
        es_valido = True
        # Validar el folio, separar el número y el año
        folio = form.folio.data.strip()
        numero_folio = None
        anio_folio = None
        try:
            numero_folio, anio_folio = validar_folio(folio)
        except ValueError as error:
            flash(str(error), "warning")
            es_valido = False
        # Si es válido
        if es_valido:
            # Cambiar el Autor al firmante
            ofi_documento.usuario = current_user
            # Guardar en la base de datos
            ofi_documento.descripcion = safe_string(form.descripcion.data, save_enie=True)
            ofi_documento.folio = folio
            ofi_documento.folio_anio = anio_folio
            ofi_documento.folio_num = numero_folio
            ofi_documento.estado = "FIRMADO"
            ofi_documento.firma_simple_usuario_id = current_user.id
            ofi_documento.firma_simple_tiempo = datetime.now()
            ofi_documento.firma_simple = OfiDocumento.elaborar_firma(ofi_documento)
            ofi_documento.save()
            # Agregar registro a la bitácora
            bitacora = Bitacora(
                modulo=Modulo.query.filter_by(nombre=MODULO).first(),
                usuario=current_user,
                descripcion=safe_message(f"Firmado simple Ofi Documento {ofi_documento.descripcion}"),
                url=url_for("ofi_documentos.detail", ofi_documento_id=ofi_documento.id),
            )
            bitacora.save()
            flash(bitacora.descripcion, "success")
            return redirect(bitacora.url)
    # Cargar los datos en el formulario
    form.descripcion.data = ofi_documento.descripcion
    form.folio.data = ofi_documento.folio if ofi_documento.folio else "0/2025"
    form.contenido_md.data = ofi_documento.contenido_md
    form.contenido_html.data = ofi_documento.contenido_html
    form.contenido_sfdt.data = ofi_documento.contenido_sfdt
    # Si está definida la variable de entorno SYNCFUSION_LICENSE_KEY
    if current_app.config.get("SYNCFUSION_LICENSE_KEY"):
        # Entregar sign_syncfusion_document.jinja2
        return render_template(
            "ofi_documentos/sign_syncfusion_document.jinja2",
            form=form,
            ofi_documento=ofi_documento,
            syncfusion_license_key=current_app.config["SYNCFUSION_LICENSE_KEY"],
        )
    # De lo contrario, entregar sign_ckeditor5.jinja2
    return render_template(
        "ofi_documentos/sign_ckeditor5.jinja2",
        form=form,
        ofi_documento=ofi_documento,
    )


@ofi_documentos.route("/ofi_documentos/enviar/<ofi_documento_id>")
@permission_required(MODULO, Permiso.MODIFICAR)
def send(ofi_documento_id):
    """Enviar un Ofi Documento"""
    # Validar que el usuario tenga el rol ESCRITOR o FIRMANTE, para que un ADMINISTRADOR no pueda enviar
    roles = current_user.get_roles()
    if ROL_ESCRITOR not in roles and ROL_FIRMANTE not in roles:
        flash("Se necesitan roles de ESCRITOR o FIRMANTE para enviar un oficio", "warning")
        return redirect(url_for("ofi_documentos.list_active"))
    # Consultar el oficio
    ofi_documento_id = safe_uuid(ofi_documento_id)
    if not ofi_documento_id:
        flash("ID de oficio inválido", "warning")
        return redirect(url_for("ofi_documentos.list_active"))
    ofi_documento = OfiDocumento.query.get_or_404(ofi_documento_id)
    # Validar que la autoridad del oficio sea la misma que la del usuario
    if ofi_documento.usuario.autoridad_id != current_user.autoridad_id:
        flash("No tienes permiso para enviar este oficio, pertenece a otra autoridad", "warning")
        return redirect(url_for("ofi_documentos.list_active"))
    # Validar el estatus, que no esté eliminado
    if ofi_documento.estatus != "A":
        flash("El oficio está eliminado", "warning")
        return redirect(url_for("ofi_documentos.detail", ofi_documento_id=ofi_documento.id))
    # Validar que tenga el estado FIRMADO
    if ofi_documento.estado != "FIRMADO":
        flash("El oficio no está en estado FIRMADO, no se puede enviar", "warning")
        return redirect(url_for("ofi_documentos.detail", ofi_documento_id=ofi_documento.id))
    # Validar que no esté archivado
    if ofi_documento.esta_archivado:
        flash("El oficio está archivado", "warning")
        return redirect(url_for("ofi_documentos.detail", ofi_documento_id=ofi_documento.id))
    # Validar que haya al menos un destinatario
    cantidad_destinatarios = (
        OfiDocumentoDestinatario.query.filter_by(ofi_documento_id=ofi_documento.id).filter_by(estatus="A").count()
    )
    if cantidad_destinatarios == 0:
        flash("Este oficio NO tiene destinatarios, no se puede enviar, debe agregarlos", "danger")
        return redirect(url_for("ofi_documentos.detail", ofi_documento_id=ofi_documento.id))
    # Actualizar el estado a ENVIADO
    ofi_documento.estado = "ENVIADO"
    ofi_documento.enviado_tiempo = datetime.now()
    ofi_documento.save()
    # TODO: Ejecutar la tarea en el fondo para enviar un mensaje a cada destinatario
    # Agregar registro a la bitácora
    bitacora = Bitacora(
        modulo=Modulo.query.filter_by(nombre=MODULO).first(),
        usuario=current_user,
        descripcion=safe_message(f"Enviado Ofi Documento {ofi_documento.descripcion}"),
        url=url_for("ofi_documentos.detail", ofi_documento_id=ofi_documento.id),
    )
    bitacora.save()
    flash(bitacora.descripcion, "success")
    # Redirigir al detalle del oficio
    return redirect(url_for("ofi_documentos.detail", ofi_documento_id=ofi_documento.id))


@ofi_documentos.route("/ofi_documentos/cancelar/<ofi_documento_id>")
@permission_required(MODULO, Permiso.MODIFICAR)
def cancel(ofi_documento_id):
    """Cancelar Ofi Documento"""
    # Validar que el usuario tenga el rol ESCRITOR o FIRMANTE, para que un ADMINISTRADOR no pueda cancelar
    roles = current_user.get_roles()
    if ROL_ESCRITOR not in roles and ROL_FIRMANTE not in roles:
        flash("Se necesitan roles de ESCRITOR o FIRMANTE para cancelar un oficio", "warning")
        return redirect(url_for("ofi_documentos.list_active"))
    # Consultar el oficio
    ofi_documento_id = safe_uuid(ofi_documento_id)
    if not ofi_documento_id:
        flash("ID de oficio inválido", "warning")
        return redirect(url_for("ofi_documentos.list_active"))
    ofi_documento = OfiDocumento.query.get_or_404(ofi_documento_id)
    # Validar que la autoridad del oficio sea la misma que la del usuario
    if ofi_documento.usuario.autoridad_id != current_user.autoridad_id:
        flash("No tienes permiso para cancelar este oficio, pertenece a otra autoridad", "warning")
        return redirect(url_for("ofi_documentos.list_active"))
    # Validar que no esté archivado
    if ofi_documento.esta_archivado:
        flash("El oficio ya está archivado", "warning")
        return redirect(url_for("ofi_documentos.detail", ofi_documento_id=ofi_documento.id))
    # Validar que SI esté cancelado
    if ofi_documento.esta_cancelado is True:
        flash("El oficio ya está caneclado", "warning")
        return redirect(url_for("ofi_documentos.detail", ofi_documento_id=ofi_documento.id))
    # Validar que NO esté enviado
    if ofi_documento.estado == "ENVIADO":
        flash("El oficio ya está enviado, no puede ser cancelado", "warning")
        return redirect(url_for("ofi_documentos.detail", ofi_documento_id=ofi_documento.id))
    # Actualizar esta_cancelado a verdadero
    ofi_documento.esta_cancelado = True
    ofi_documento.save()
    # Agregar registro a la bitácora
    bitacora = Bitacora(
        modulo=Modulo.query.filter_by(nombre=MODULO).first(),
        usuario=current_user,
        descripcion=safe_message(f"Cancelado Oficio Documento {ofi_documento.descripcion}"),
        url=url_for("ofi_documentos.detail", ofi_documento_id=ofi_documento.id),
    )
    bitacora.save()
    flash(bitacora.descripcion, "success")
    # Redirigir al detalle del oficio
    return redirect(url_for("ofi_documentos.detail", ofi_documento_id=ofi_documento.id))


@ofi_documentos.route("/ofi_documentos/descancelar/<ofi_documento_id>")
@permission_required(MODULO, Permiso.MODIFICAR)
def uncancel(ofi_documento_id):
    """Descancelar Ofi Documento"""
    # Validar que el usuario tenga el rol ESCRITOR o FIRMANTE, para que un ADMINISTRADOR no pueda descancelar
    roles = current_user.get_roles()
    if ROL_ESCRITOR not in roles and ROL_FIRMANTE not in roles:
        flash("Se necesitan roles de ESCRITOR o FIRMANTE para descancelar un oficio", "warning")
        return redirect(url_for("ofi_documentos.list_active"))
    # Consultar el oficio
    ofi_documento_id = safe_uuid(ofi_documento_id)
    if not ofi_documento_id:
        flash("ID de oficio inválido", "warning")
        return redirect(url_for("ofi_documentos.list_active"))
    ofi_documento = OfiDocumento.query.get_or_404(ofi_documento_id)
    # Validar que la autoridad del oficio sea la misma que la del usuario
    if ofi_documento.usuario.autoridad_id != current_user.autoridad_id:
        flash("No tienes permiso para descancelar este oficio, pertenece a otra autoridad", "warning")
        return redirect(url_for("ofi_documentos.detail", ofi_documento_id=ofi_documento.id))
    # Validar que no esté archivado
    if ofi_documento.esta_archivado:
        flash("El oficio ya está archivado", "warning")
        return redirect(url_for("ofi_documentos.detail", ofi_documento_id=ofi_documento.id))
    # Validar que NO esté cancelado
    if ofi_documento.esta_cancelado is False:
        flash("El oficio no está cancelado", "warning")
        return redirect(url_for("ofi_documentos.detail", ofi_documento_id=ofi_documento.id))
    # Actualizar esta_cancelado a falso
    ofi_documento.esta_cancelado = False
    ofi_documento.save()
    bitacora = Bitacora(
        modulo=Modulo.query.filter_by(nombre=MODULO).first(),
        usuario=current_user,
        descripcion=safe_message(f"Descancelado Oficio Documento {ofi_documento.descripcion}"),
        url=url_for("ofi_documentos.detail", ofi_documento_id=ofi_documento.id),
    )
    bitacora.save()
    flash(bitacora.descripcion, "success")
    # Redirigir al detalle del oficio
    return redirect(url_for("ofi_documentos.detail", ofi_documento_id=ofi_documento.id))


@ofi_documentos.route("/ofi_documentos/responder/<ofi_documento_id>", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.CREAR)
def response(ofi_documento_id):
    """Responder un Ofi Documento"""
    # Validar que el usuario tenga el rol ESCRITOR o FIRMANTE, para que un ADMINISTRADOR no pueda responder
    roles = current_user.get_roles()
    if ROL_ESCRITOR not in roles and ROL_FIRMANTE not in roles:
        flash("Se necesitan roles de ESCRITOR o FIRMANTE para reponder un oficio", "warning")
        return redirect(url_for("ofi_documentos.list_active"))
    # Consultar el oficio
    ofi_documento_id = safe_uuid(ofi_documento_id)
    if not ofi_documento_id:
        flash("ID de oficio inválido", "warning")
        return redirect(url_for("ofi_documentos.list_active"))
    ofi_documento = OfiDocumento.query.get_or_404(ofi_documento_id)
    # Validar que no esté eliminado
    if ofi_documento.estatus != "A":
        flash("El oficio al que quiere responder está eliminado", "warning")
        return redirect(url_for("ofi_documentos.list_active"))
    # Validar que el estado sea FIRMADO o ENVIADO
    if ofi_documento.estado != "FIRMADO" and ofi_documento.estado != "ENVIADO":
        flash("El oficio al que quiere responder NO está FIRMADO o ENVIADO", "warning")
        return redirect(url_for("ofi_documentos.list_active"))
    # Validar que el usuario sea un destinatario de este oficio
    usuario_destinatario = (
        OfiDocumentoDestinatario.query.filter_by(ofi_documento_id=ofi_documento.id)
        .filter_by(usuario_id=current_user.id)
        .first()
    )
    if usuario_destinatario is None:
        flash("No eres detinatario de este oficio NO tienes permiso para responder", "warning")
        return redirect(url_for("ofi_documentos.list_active"))
    # TODO: Cambiar a mostrar un formulario donde se pueda escoger una plantilla
    # Consultar la primer plantilla de su autoridad
    ofi_plantilla = (
        OfiPlantilla.query.join(Usuario)
        .filter(Usuario.autoridad_id == current_user.autoridad_id)
        .filter(OfiPlantilla.estatus == "A")
        .filter(OfiPlantilla.esta_archivado == False)
        .first()
    )
    if ofi_plantilla is None:
        flash("No hay una plantilla para crear un oficio de respuesta", "warning")
        return redirect(url_for("ofi_documentos.detail", ofi_documento_id=ofi_documento_id))
    # Formulario
    form = OfiDocumentoNewForm()
    # Cargar los datos de la plantilla en el formulario
    form.descripcion.data = "RE: " + ofi_plantilla.descripcion
    form.contenido_md.data = ofi_plantilla.contenido_md
    form.contenido_html.data = ofi_plantilla.contenido_html
    form.contenido_sfdt.data = ofi_plantilla.contenido_sfdt
    form.cadena_oficio_id.data = ofi_documento_id
    # Si está definida la variable de entorno SYNCFUSION_LICENSE_KEY
    if current_app.config.get("SYNCFUSION_LICENSE_KEY"):
        # Entregar new_syncfusion_document.jinja2
        return render_template(
            "ofi_documentos/new_syncfusion_document.jinja2",
            form=form,
            ofi_plantilla_id=ofi_plantilla.id,
            syncfusion_license_key=current_app.config["SYNCFUSION_LICENSE_KEY"],
        )
    # De lo contrario, entregar new_ckeditor5.jinja2
    return render_template(
        "ofi_documentos/new_ckeditor5.jinja2",
        form=form,
        ofi_plantilla_id=ofi_plantilla.id,
    )


@ofi_documentos.route("/ofi_documentos/archivar/<ofi_documento_id>")
@permission_required(MODULO, Permiso.MODIFICAR)
def archive(ofi_documento_id):
    """Archivar Ofi Documento"""
    # Validar que el usuario tenga el rol ESCRITOR o FIRMANTE, para que un ADMINISTRADOR no pueda cancelar
    roles = current_user.get_roles()
    if ROL_ESCRITOR not in roles and ROL_FIRMANTE not in roles:
        flash("Se necesitan roles de ESCRITOR o FIRMANTE para archivar un oficio", "warning")
        return redirect(url_for("ofi_documentos.list_active"))
    # Consultar el oficio
    ofi_documento_id = safe_uuid(ofi_documento_id)
    if not ofi_documento_id:
        flash("ID de oficio inválido", "warning")
        return redirect(url_for("ofi_documentos.list_active"))
    ofi_documento = OfiDocumento.query.get_or_404(ofi_documento_id)
    # Validar que la autoridad del oficio sea la misma que la del usuario
    if ofi_documento.usuario.autoridad_id != current_user.autoridad_id:
        flash("No tienes permiso para archivar este oficio, pertenece a otra autoridad", "warning")
        return redirect(url_for("ofi_documentos.list_active"))
    # Validar que no esté archivado
    if ofi_documento.esta_archivado is True:
        flash("El oficio ya está archivado", "warning")
        return redirect(url_for("ofi_documentos.detail", ofi_documento_id=ofi_documento.id))
    # Validar que SI esté cancelado
    if ofi_documento.esta_cancelado is True:
        flash("El oficio ya está caneclado", "warning")
        return redirect(url_for("ofi_documentos.detail", ofi_documento_id=ofi_documento.id))
    # Actualizar esta_archivado a verdadero
    ofi_documento.esta_archivado = True
    ofi_documento.save()
    # Agregar registro a la bitácora
    bitacora = Bitacora(
        modulo=Modulo.query.filter_by(nombre=MODULO).first(),
        usuario=current_user,
        descripcion=safe_message(f"Archivando Oficio Documento {ofi_documento.descripcion}"),
        url=url_for("ofi_documentos.detail", ofi_documento_id=ofi_documento.id),
    )
    bitacora.save()
    flash(bitacora.descripcion, "success")
    # Redirigir al detalle del oficio
    return redirect(url_for("ofi_documentos.detail", ofi_documento_id=ofi_documento.id))


@ofi_documentos.route("/ofi_documentos/desarchivar/<ofi_documento_id>")
@permission_required(MODULO, Permiso.MODIFICAR)
def unarchive(ofi_documento_id):
    """Desarchivar Ofi Documento"""
    # Validar que el usuario tenga el rol ESCRITOR o FIRMANTE, para que un ADMINISTRADOR no pueda desarchivar
    roles = current_user.get_roles()
    if ROL_ESCRITOR not in roles and ROL_FIRMANTE not in roles:
        flash("Se necesitan roles de ESCRITOR o FIRMANTE para desarchivar un oficio", "warning")
        return redirect(url_for("ofi_documentos.list_active"))
    # Consultar el oficio
    ofi_documento_id = safe_uuid(ofi_documento_id)
    if not ofi_documento_id:
        flash("ID de oficio inválido", "warning")
        return redirect(url_for("ofi_documentos.list_active"))
    ofi_documento = OfiDocumento.query.get_or_404(ofi_documento_id)
    # Validar que la autoridad del oficio sea la misma que la del usuario
    if ofi_documento.usuario.autoridad_id != current_user.autoridad_id:
        flash("No tienes permiso para desarchivar este oficio, pertenece a otra autoridad", "warning")
        return redirect(url_for("ofi_documentos.detail", ofi_documento_id=ofi_documento.id))
    # Validar que no esté archivado
    if ofi_documento.esta_archivado is False:
        flash("El oficio NO está archivado", "warning")
        return redirect(url_for("ofi_documentos.detail", ofi_documento_id=ofi_documento.id))
    # Validar que está cancelado
    if ofi_documento.esta_cancelado:
        flash("El oficio está cancelado", "warning")
        return redirect(url_for("ofi_documentos.detail", ofi_documento_id=ofi_documento.id))
    # Actualizar esta_archivado a falso
    ofi_documento.esta_archivado = False
    ofi_documento.save()
    bitacora = Bitacora(
        modulo=Modulo.query.filter_by(nombre=MODULO).first(),
        usuario=current_user,
        descripcion=safe_message(f"Desarchivar Oficio Documento {ofi_documento.descripcion}"),
        url=url_for("ofi_documentos.detail", ofi_documento_id=ofi_documento.id),
    )
    bitacora.save()
    flash(bitacora.descripcion, "success")
    # Redirigir al detalle del oficio
    return redirect(url_for("ofi_documentos.detail", ofi_documento_id=ofi_documento.id))


@ofi_documentos.route("/ofi_documentos/eliminar/<ofi_documento_id>")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def delete(ofi_documento_id):
    """Eliminar Ofi Documento"""
    # Consultar el oficio
    ofi_documento_id = safe_uuid(ofi_documento_id)
    if not ofi_documento_id:
        flash("ID de oficio inválido", "warning")
        return redirect(url_for("ofi_documentos.list_active"))
    ofi_documento = OfiDocumento.query.get_or_404(ofi_documento_id)
    # Validar el estatus, que no esté eliminado
    if ofi_documento.estatus != "A":
        flash("El oficio ya está eliminado", "warning")
        return redirect(url_for("ofi_documentos.detail", ofi_documento_id=ofi_documento.id))
    # Eliminar el oficio
    ofi_documento.delete()
    bitacora = Bitacora(
        modulo=Modulo.query.filter_by(nombre=MODULO).first(),
        usuario=current_user,
        descripcion=safe_message(f"Eliminado Oficio Documento {ofi_documento.descripcion}"),
        url=url_for("ofi_documentos.detail", ofi_documento_id=ofi_documento.id),
    )
    bitacora.save()
    flash(bitacora.descripcion, "success")
    return redirect(url_for("ofi_documentos.detail", ofi_documento_id=ofi_documento.id))


@ofi_documentos.route("/ofi_documentos/recuperar/<ofi_documento_id>")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def recover(ofi_documento_id):
    """Recuperar Ofi Documento"""
    # Consultar el oficio
    ofi_documento_id = safe_uuid(ofi_documento_id)
    if not ofi_documento_id:
        flash("ID de oficio inválido", "warning")
        return redirect(url_for("ofi_documentos.list_active"))
    ofi_documento = OfiDocumento.query.get_or_404(ofi_documento_id)
    # Validar el estatus, que esté eliminado
    if ofi_documento.estatus != "B":
        flash("El oficio no está eliminado", "warning")
        return redirect(url_for("ofi_documentos.detail", ofi_documento_id=ofi_documento.id))
    # Recuperar el oficio
    ofi_documento.recover()
    bitacora = Bitacora(
        modulo=Modulo.query.filter_by(nombre=MODULO).first(),
        usuario=current_user,
        descripcion=safe_message(f"Recuperado Oficio Documento {ofi_documento.descripcion}"),
        url=url_for("ofi_documentos.detail", ofi_documento_id=ofi_documento.id),
    )
    bitacora.save()
    flash(bitacora.descripcion, "success")
    return redirect(url_for("ofi_documentos.detail", ofi_documento_id=ofi_documento.id))
