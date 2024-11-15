"""
CLI Google AI Studio
"""

import os

import click
from dotenv import load_dotenv

import google.generativeai as genai

load_dotenv()

AI_STUDIO_API_KEY = os.getenv("AI_STUDIO_API_KEY", "")
MODEL_NAME = "gemini-1.0-pro"


@click.group()
def cli():
    """Google AI Studio"""


@click.command()
def listar_modelos():
    """Listar modelos"""
    click.echo("Listar los modelos")

    # Cargar API key
    genai.configure(api_key=AI_STUDIO_API_KEY)

    # Listar los modelos
    for m in genai.list_models():
        if "generateContent" in m.supported_generation_methods:
            click.echo(m.name)


@click.command()
@click.argument("pregunta", type=str)
def preguntar(pregunta):
    """Preguntar"""
    click.echo("Preguntar")

    # Cargar API key
    genai.configure(api_key=AI_STUDIO_API_KEY)

    # Crear modelo
    model = genai.GenerativeModel(MODEL_NAME)

    # Generar contenido
    response = model.generate_content(pregunta)

    # Mostrar respuesta
    click.echo(click.style(f"Respuesta: {response.text}", fg="blue"))

    # Mostrar el feedback del prompt
    click.echo(click.style(f"Feedback: {response.prompt_feedback}", fg="green"))


@click.command()
@click.option("--saludo", type=str, default="")
def chatear(saludo):
    """Chatear"""
    click.echo("Chatear")

    # Cargar API key
    genai.configure(api_key=AI_STUDIO_API_KEY)

    # Crear modelo
    model = genai.GenerativeModel(MODEL_NAME)

    # Inicializar el chat
    chat = model.start_chat()

    # Si saludo no está vacío, enviar y mostrar la respuesta
    if saludo != "":
        response = chat.send_message(saludo)
        click.echo(click.style(f"Gemini: {response.text}", fg="blue"))

    # Bucle para preguntar y mostrar la respuesta, terminar con "salir"
    while True:
        # Leer la pregunta
        pregunta = input("Tú: ")

        # Salir
        if pregunta == "salir":
            break

        # Enviar y mostrar la respuesta
        response = chat.send_message(pregunta)
        click.echo(click.style(f"Gemini: {response.text}", fg="blue"))

    # Mostrar un mensaje de despedida
    click.echo("Adiós")


cli.add_command(listar_modelos)
cli.add_command(preguntar)
cli.add_command(chatear)
