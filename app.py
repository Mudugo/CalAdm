from flask import Flask, render_template, request, send_file
from datetime import datetime, timedelta
import calendar
import zipfile
from fpdf import FPDF
from io import BytesIO

app = Flask(__name__)

def calcular_dias_trabalho(data_admissao, escala):
    escalas = {
        "12x36": (1, 1),
        "5x2": "dias_uteis",
        "4x2": (4, 2),
        "5x1": (5, 1),
        "6x1": (6, 1),
    }

    if escala not in escalas:
        return []

    if 1 <= data_admissao.day <= 14:
        ano, mes = data_admissao.year, data_admissao.month
        ultimo_dia_mes = calendar.monthrange(ano, mes)[1]
        data_fim = datetime(ano, mes, ultimo_dia_mes)
    else:
        ano, mes = data_admissao.year, data_admissao.month
        proximo_mes = mes + 1 if mes < 12 else 1
        ano_proximo = ano if mes < 12 else ano + 1
        ultimo_dia_proximo_mes = calendar.monthrange(ano_proximo, proximo_mes)[1]
        data_fim = datetime(ano_proximo, proximo_mes, ultimo_dia_proximo_mes)

    if escala == "5x2":
        return obter_dias_uteis(data_admissao, data_fim)

    return obter_escala_trabalho(data_admissao, data_fim, escalas[escala])

def calcular_dias_beneficio_por_mes(data_admissao, escala):

    dias_por_mes = {}
    escalas = {
        "12x36": (1, 1),
        "5x2": "dias_uteis",
        "4x2": (4, 2),
        "5x1": (5, 1),
        "6x1": (6, 1),
    }

    if escala not in escalas:
        return dias_por_mes

    if 1 <= data_admissao.day <= 14:
        ano, mes = data_admissao.year, data_admissao.month
        ultimo_dia_mes = calendar.monthrange(ano, mes)[1]
        data_fim = datetime(ano, mes, ultimo_dia_mes)
    else:
        ano, mes = data_admissao.year, data_admissao.month
        proximo_mes = mes + 1 if mes < 12 else 1
        ano_proximo = ano if mes < 12 else ano + 1
        ultimo_dia_proximo_mes = calendar.monthrange(ano_proximo, proximo_mes)[1]
        data_fim = datetime(ano_proximo, proximo_mes, ultimo_dia_proximo_mes)

    if escala == "5x2":
        dias_trabalho = obter_dias_uteis(data_admissao, data_fim)
    else:
        dias_trabalho = obter_escala_trabalho(data_admissao, data_fim, escalas[escala])

    # Discriminar dias por mês
    for dia in dias_trabalho:
        mes_ano = f"{calendar.month_name[dia.month][:3]}/{dia.year}"
        dias_por_mes[mes_ano] = dias_por_mes.get(mes_ano, 0) + 1

    return dias_por_mes

def obter_dias_uteis(data_admissao, data_fim):
    dias_trabalho = []
    data_atual = data_admissao
    while data_atual <= data_fim:
        if data_atual.weekday() < 5:
            dias_trabalho.append(data_atual)
        data_atual += timedelta(days=1)
    return dias_trabalho

def obter_escala_trabalho(data_admissao, data_fim, escala):
    dias_trabalho, dias_folga = escala
    cronograma = []
    data_atual = data_admissao
    while data_atual <= data_fim:
        for _ in range(dias_trabalho):
            if data_atual > data_fim:
                break
            cronograma.append(data_atual)
            data_atual += timedelta(days=1)
        data_atual += timedelta(days=dias_folga)
    return cronograma

def calcular_total_vt(valor_vt, dias_trabalho, feriados):
    feriados = int(feriados)
    total_dias = len(dias_trabalho) - feriados
    return valor_vt * total_dias

def calcular_total_vr(dias_trabalho, feriados):
    feriados = int(feriados)
    total_dias = len(dias_trabalho)  - feriados
    return 19.77 * total_dias

def parcela_vt(valor_vt, total_vt):
    quociente = int(float(total_vt) // (float(valor_vt) * 6))
    resto = total_vt % (float(valor_vt) * 6)
    
    parcelas_vt = [(float(valor_vt) * 6)] * quociente
    
    if resto > 0:
        parcelas_vt.append(resto)
    
    if len(parcelas_vt) > 1 and parcelas_vt[-1] < (float(valor_vt) * 6):
        parcelas_vt[-2] += parcelas_vt[-1]
        parcelas_vt.pop()
    
    return parcelas_vt

def parcela_vr(total_vr):
    quociente = int(float(total_vr) // (float(19.77) * 6))
    resto = total_vr % (float(19.77) * 6)
    
    parcelas_vr = [(float(19.77) * 6)] * quociente
    
    if resto > 0:
        parcelas_vr.append(resto)
    
    if len(parcelas_vr) > 1 and parcelas_vr[-1] < (float(19.77) * 6):
        parcelas_vr[-2] += parcelas_vr[-1]
        parcelas_vr.pop()
        
    return parcelas_vr

def gerar_pdf(dados, is_vr=False, parcelas=None, imagem_path=None):
    buffer = BytesIO()
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    # Adicionar imagem se houver
    if imagem_path:
        pdf.image(imagem_path, x=10, y=5, w=50, h=25)

    # Título
    pdf.set_font('Arial', 'B', 16)
    titulo = f"{'VR' if is_vr else 'VT'} Inicial"
    pdf.cell(200, 10, txt=titulo, ln=True, align='C')

    pdf.ln(10)  # Quebra de linha

    pdf.set_font('Arial', 'B', 16)
    titulo1 = f"{dados['nome']}"
    pdf.cell(200, 20, txt=titulo1, ln=True, align='C')

    pdf.ln(10)  # Quebra de linha
    
    pdf.set_font('Arial', 'B', 16)
    titulo2 = f"{dados['data_admissao']}"
    pdf.cell(200, 30, txt=titulo2, ln=True, align='C')

    # Adicionar informações do funcionário
    pdf.set_font('Arial', '', 12)
    campos = [
        ("Nome Completo", dados["nome"]),
        ("Empresa", dados["empresa"]),
        ("Cliente", dados["cliente"]),
        ("Data de Admissão", dados["data_admissao"]),
        ("Escala de Trabalho", dados["escala"]),
        ("Função", dados["cargo"]),
        ("Horário", dados["turno"]),
        ("Banco", dados["banco"]),
        ("Tipo de chave Pix", dados["tipo_pix"]),
        ("Chave Pix", dados["chave_pix"]),
    ]

    for campo, valor in campos:
        pdf.cell(0, 10, f"{campo}: {valor}", ln=True)

    # Dias de Benefício
    pdf.cell(0, 10, "Dias de Benefício:", ln=True)
    for mes_ano, dias in dados["dias_beneficio"].items():
        pdf.cell(0, 10, f"  {mes_ano}: {dias} dias", ln=True)

    # Total do Benefício
    total = dados["total_vr"] if is_vr else dados["total_vt"]
    pdf.cell(0, 10, f"Valor Total do Benefício: R$ {round(total, 2)}", ln=True)

    # Parcelas
    if parcelas:
        pdf.cell(0, 10, "Parcelas:", ln=True)
        quarta_base = datetime.strptime(dados["data_admissao"], "%Y-%m-%d")
        while quarta_base.weekday() != 2:  # Encontrar a próxima quarta-feira
            quarta_base += timedelta(days=1)

        for i, parcela in enumerate(parcelas, start=1):
            quarta_data = quarta_base + timedelta(weeks=(i - 1))  # Incrementa por semana
            pdf.cell(0, 10, f"  Parcela {i}: R$ {round(parcela, 2)} - {quarta_data.strftime('%d/%m/%Y')}", ln=True)

    # Gerar PDF
    pdf.output(buffer)
    buffer.seek(0)
    return buffer

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        try:
            nome = request.form.get("nome")
            empresa = request.form.get("empresa")
            cliente = request.form.get("cliente")
            data_admissao_str = request.form.get("data_admissao")
            escala = request.form.get("escala")
            cargo = request.form.get("cargo")
            turno = request.form.get("turno")
            banco = request.form.get("banco")
            tipo_pix = request.form.get("tipo_pix")
            chave_pix = request.form.get("chave_pix")
            valor_vt1 = float(request.form.get("valor_vt"))
            valor_vt = valor_vt1 * 2
            feriados = int(request.form.get("feriados"))  # Captura o valor dos feriados

            data_admissao = datetime.strptime(data_admissao_str, "%Y-%m-%d")
            dias_trabalho = calcular_dias_trabalho(data_admissao, escala)

            # Atualiza para descontar os feriados dos dias de benefício
            dias_beneficio = calcular_dias_beneficio_por_mes(data_admissao, escala)
            for mes_ano, dias in dias_beneficio.items():
                dias_beneficio[mes_ano] = max(0, dias - feriados)  # Subtrai feriados e não permite valores negativos

            total_vt = calcular_total_vt(valor_vt, dias_trabalho, feriados)
            parcelas_vt = parcela_vt(valor_vt, total_vt)
            total_vr = calcular_total_vr(dias_trabalho, feriados)
            parcelas_vr = parcela_vr(total_vr)

            dados = {
                "nome": nome,
                "empresa": empresa,
                "cliente": cliente,
                "data_admissao": data_admissao_str,
                "escala": escala,
                "cargo": cargo,
                "turno": turno,
                "banco": banco,
                "tipo_pix": tipo_pix,
                "chave_pix": chave_pix,
                "total_vt": total_vt,
                "total_vr": total_vr,
                "dias_beneficio": dias_beneficio,
            }

            imagem_path = r"logo.png"  # Caminho absoluto da imagem
            pdf_buffer_vt = gerar_pdf(dados, parcelas=parcelas_vt, imagem_path=imagem_path)
            pdf_buffer_vr = gerar_pdf(dados, is_vr=True, parcelas=parcelas_vr, imagem_path=imagem_path)

            zip_buffer = BytesIO()
            with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
                zip_file.writestr(f"{nome}_{data_admissao_str}_VT.pdf", pdf_buffer_vt.getvalue())
                zip_file.writestr(f"{nome}_{data_admissao_str}_VR.pdf", pdf_buffer_vr.getvalue())

            zip_buffer.seek(0)
            return send_file(
                zip_buffer,
                as_attachment=True,
                download_name=f"{nome}_{data_admissao_str}_relatorios.zip",
                mimetype="application/zip",
            )
        except ValueError:
            return render_template("index.html", error="O valor de VT deve ser um número válido.")

    return render_template("index.html")


if __name__ == "__main__":
    app.run(debug=True)
