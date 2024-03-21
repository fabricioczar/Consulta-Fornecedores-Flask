from flask import Flask, render_template, request
import json
import requests
from datetime import datetime

app = Flask(__name__)

def consultar_certidoes_tcu(cnpjs):
    base_url = "https://certidoes-apf.apps.tcu.gov.br/api/rest/publico/certidoes/"
    resultados = []

    for cnpj in cnpjs:
        url = base_url + cnpj
        response = requests.get(url)

        if response.status_code == 200:
            json_data = response.json()
            status_certidoes = [certidao.get("situacao") for certidao in json_data.get("certidoes", [])]
            if "NADA_CONSTA" in status_certidoes:
                resultados.append({
                    "fornecedor": json_data["razaoSocial"],
                    "cnpj": cnpj,
                    "certidao_tcu": {"url": url, "status": "OK"}
                })
            else:
                emissores_inabilitados = [certidao.get("emissor") for certidao in json_data.get("certidoes", [])]
                resultados.append({
                    "fornecedor": json_data["razaoSocial"],
                    "cnpj": cnpj,
                    "certidao_tcu": {"url": url, "status": f"Inabilitado nos emissores: {', '.join(emissores_inabilitados)}"}
                })
        else:
            resultados.append(f"Falha ao obter dados JSON para o CNPJ {cnpj}. Status code: {response.status_code}")

    return resultados

def consultar_ocorrencias_fornecedores(cnpj):
    url = f"https://compras.dados.gov.br/fornecedores/v1/ocorrencias_fornecedores.json?cnpj={cnpj}"
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Falha ao obter dados JSON para o CNPJ {cnpj}. Status code: {response.status_code}")
        return None

def consultar_ocorrencia_por_id(id_ocorrencia):
    url = f"https://compras.dados.gov.br/fornecedores/doc/ocorrencia_fornecedor/{id_ocorrencia}.json"
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Falha ao obter dados JSON para a ocorrência de ID {id_ocorrencia}. Status code: {response.status_code}")
        return None

def verificar_ocorrencias(json_data):
    ocorrencias_encontradas = []
    for ocorrencia in json_data["_embedded"]["ocorrenciasFornecedores"]:
        tipo_ocorrencia = ocorrencia["id_tipo_ocorrencia"]
        id_ocorrencia = ocorrencia["id"]
        detalhes_ocorrencia = consultar_ocorrencia_por_id(id_ocorrencia)
        if detalhes_ocorrencia:
            data_inicial = detalhes_ocorrencia.get("data_inicial")
            data_final = detalhes_ocorrencia.get("data_final")
            if data_inicial and data_final:
                data_atual = datetime.now().date()
                data_inicial = datetime.strptime(data_inicial, "%Y-%m-%d").date()
                data_final = datetime.strptime(data_final, "%Y-%m-%d").date()
                if data_inicial <= data_atual <= data_final:
                    ocorrencias_encontradas.append({
                        "tipo_ocorrencia": tipo_ocorrencia,
                        "data_inicial": data_inicial.strftime('%d/%m/%Y'),
                        "data_final": data_final.strftime('%d/%m/%Y'),
                        "link_ocorrencia": f"https://compras.dados.gov.br/fornecedores/doc/ocorrencia_fornecedor/{id_ocorrencia}"
                    })
    return ocorrencias_encontradas

@app.route('/certidoes', methods=['GET', 'POST'])
def certidoes():
    if request.method == 'POST':
        cnpjs = request.form['cnpjs'].split()
        certidoes_detalhadas = []

        for cnpj in cnpjs:
            certidoes = consultar_certidoes_tcu([cnpj])
            for certidao in certidoes:
                ocorrencias_fornecedores = consultar_ocorrencias_fornecedores(certidao['cnpj'])
                if ocorrencias_fornecedores:
                    ocorrencias_encontradas = verificar_ocorrencias(ocorrencias_fornecedores)
                    certidao['ocorrencias'] = ocorrencias_encontradas
                certidoes_detalhadas.append(certidao)

        return render_template('index.html', certidoes=certidoes_detalhadas)

    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True)