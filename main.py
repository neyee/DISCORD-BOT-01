import discord
from discord.ext import commands
from discord import app_commands
import json
import os
from dotenv import load_dotenv
import random
import asyncio
from keep_alive import keep_alive

# Cargar variables de entorno
load_dotenv()

TOKEN = os.getenv('TOKEN') or os.environ.get('TOKEN')
ADMIN_ID = 865597179145486366  # Reemplaza con tu ID de administrador

if not TOKEN:
    raise ValueError("🔴 ¡Token no encontrado! Configúralo en Secrets (Replit) o en .env")

# Configuración del bot
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Archivos de datos
data_file = "user_data.json"  # Datos de usuarios (saldo, etc.)
bingo_file = "bingo_data.json"  # Datos del bingo (precio, cartones)

# Valores por defecto
exchange_rate = 78  # Tasa de cambio Bs. → USD
bingo_price = 1000  # Precio inicial del cartón de bingo en Bs.

# --- FUNCIONES DE CARGA/GUARDADO ---
def load_data():
    try:
        if os.path.exists(data_file):
            with open(data_file, "r", encoding='utf-8') as file:
                return json.load(file)
    except (json.JSONDecodeError, FileNotFoundError):
        return {}
    return {}

def save_data(data):
    try:
        with open(data_file, "w", encoding='utf-8') as file:
            json.dump(data, file, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f"⚠️ Error al guardar datos: {e}")

def load_bingo_data():
    try:
        if os.path.exists(bingo_file):
            with open(bingo_file, "r", encoding='utf-8') as file:
                data = json.load(file)
                # Asegurar estructura correcta
                if "price" not in data:
                    data["price"] = bingo_price
                if "tickets" not in data:
                    data["tickets"] = {}
                return data
        return {"price": bingo_price, "tickets": {}}
    except Exception as e:
        print(f"⚠️ Error al cargar datos de bingo: {e}")
        return {"price": bingo_price, "tickets": {}}

def save_bingo_data(data):
    try:
        with open(bingo_file, "w", encoding='utf-8') as file:
            json.dump(data, file, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f"⚠️ Error al guardar datos de bingo: {e}")

# --- FUNCIONES DE BINGO ---
def generate_bingo_card():
    """Genera un cartón de bingo 3x3 con números únicos (1-50)"""
    try:
        numbers = random.sample(range(1, 51), 9)
        return [numbers[i*3:(i+1)*3] for i in range(3)]
    except Exception as e:
        print(f"⚠️ Error al generar cartón: {e}")
        return [[1, 2, 3], [4, 5, 6], [7, 8, 9]]  # Cartón por defecto en caso de error

def format_bingo_card(card):
    """Formatea el cartón para mostrarlo en un mensaje"""
    try:
        return "\n".join(" | ".join(f"{n:2}" for n in row) for row in card)
    except Exception as e:
        print(f"⚠️ Error al formatear cartón: {e}")
        return "1 | 2 | 3\n4 | 5 | 6\n7 | 8 | 9"  # Formato por defecto

def generate_seed_phrase():
    words = ["manzana", "perro", "flor", "sol", "luna", "rojo", "azul", "libro", "feliz", "montaña"]
    return " ".join(random.sample(words, 3))

# --- EVENTOS ---
@bot.event
async def on_ready():
    try:
        print(f'✅ Bot conectado como {bot.user.name}')
        
        # Cargar configuración de bingo
        bingo_data = load_bingo_data()
        global bingo_price
        bingo_price = bingo_data.get("price", 1000)
        
        await bot.change_presence(activity=discord.Game(name=f"Bingo | Tasa: {exchange_rate} | Cartón: Bs.{bingo_price}"))
        
        # Sincronizar comandos slash
        try:
            synced = await bot.tree.sync()
            print(f"🔹 Comandos sincronizados: {len(synced)}")
        except Exception as e:
            print(f"🔴 Error al sincronizar comandos: {e}")
            
    except Exception as e:
        print(f"🔴 Error crítico en on_ready: {e}")

# --- COMANDOS DE USUARIO ---
@bot.tree.command(name="crear_cuenta", description="Crea una cuenta para usar el sistema de bingo")
async def crear_cuenta(interaction: discord.Interaction):
    try:
        data = load_data()
        user_id = str(interaction.user.id)
        
        if user_id in data:
            await interaction.response.send_message("🔴 ¡Ya tienes una cuenta creada!", ephemeral=True)
            return
        
        # Crear cuenta con saldo inicial 0
        data[user_id] = {
            "balance": 0.0,
            "seed_phrase": generate_seed_phrase()
        }
        save_data(data)
        
        try:
            embed = discord.Embed(
                title="✅ Cuenta Creada",
                description=f"**Frase de recuperación:** ||{data[user_id]['seed_phrase']}||\n\nGuárdala en un lugar seguro.",
                color=discord.Color.green()
            )
            await interaction.user.send(embed=embed)
            await interaction.response.send_message("📩 Revisa tus mensajes privados.", ephemeral=True)
        except discord.Forbidden:
            await interaction.response.send_message("🔴 No puedo enviarte DMs. ¡Habilita mensajes privados!", ephemeral=True)
            
    except Exception as e:
        print(f"⚠️ Error en crear_cuenta: {e}")
        await interaction.response.send_message("🔴 Ocurrió un error al crear la cuenta", ephemeral=True)

@bot.tree.command(name="saldo", description="Consulta tu saldo en Bs. y USD")
async def saldo(interaction: discord.Interaction):
    try:
        data = load_data()
        user_id = str(interaction.user.id)
        
        if user_id not in data:
            await interaction.response.send_message("🔴 Primero crea una cuenta con /crear_cuenta", ephemeral=True)
            return
        
        balance = data[user_id]["balance"]
        usd_balance = balance / exchange_rate
        
        embed = discord.Embed(
            title="💰 Tu Saldo",
            description=f"**Bs.** {balance:,.2f}\n**USD** ${usd_balance:,.2f}",
            color=discord.Color.blue()
        )
        embed.set_footer(text=f"Tasa de cambio: 1 USD = {exchange_rate} Bs.")
        await interaction.response.send_message(embed=embed)
    except Exception as e:
        print(f"⚠️ Error en saldo: {e}")
        await interaction.response.send_message("🔴 Error al consultar saldo", ephemeral=True)

@bot.tree.command(name="comprar_carton", description="Compra un cartón de bingo")
async def comprar_carton(interaction: discord.Interaction):
    try:
        user_id = str(interaction.user.id)
        user_data = load_data()
        bingo_data = load_bingo_data()
        
        # Verificar cuenta
        if user_id not in user_data:
            await interaction.response.send_message("🔴 Primero crea una cuenta con /crear_cuenta", ephemeral=True)
            return
        
        # Verificar saldo
        price = bingo_data.get("price", bingo_price)
        if user_data[user_id]["balance"] < price:
            await interaction.response.send_message(
                f"🔴 Saldo insuficiente. Necesitas Bs. {price:,.2f}\n(Tu saldo: Bs. {user_data[user_id]['balance']:,.2f})",
                ephemeral=True
            )
            return
        
        # Generar cartón
        card = generate_bingo_card()
        
        # Actualizar saldo
        user_data[user_id]["balance"] -= price
        save_data(user_data)
        
        # Guardar cartón
        bingo_data["tickets"][user_id] = card
        save_bingo_data(bingo_data)
        
        # Enviar cartón por DM
        try:
            embed = discord.Embed(
                title="🎟️ Cartón de Bingo",
                description=f"Comprado por Bs. {price:,.2f}",
                color=discord.Color.gold()
            )
            embed.add_field(
                name="Tus números",
                value=f"```\n{format_bingo_card(card)}\n```",
                inline=False
            )
            embed.set_footer(text="¡Buena suerte!")
            await interaction.user.send(embed=embed)
            await interaction.response.send_message("✅ Cartón comprado. Revisa tus mensajes privados.", ephemeral=True)
        except discord.Forbidden:
            await interaction.response.send_message("🔴 No puedo enviarte el cartón. ¡Habilita los mensajes privados!", ephemeral=True)
    except Exception as e:
        print(f"⚠️ Error en comprar_carton: {e}")
        await interaction.response.send_message("🔴 Error al comprar cartón", ephemeral=True)

# --- COMANDOS DE ADMIN ---
@bot.tree.command(name="set_bingo_price", description="[ADMIN] Establece el precio de los cartones")
@app_commands.describe(precio="Precio en Bs.")
async def set_bingo_price(interaction: discord.Interaction, precio: float):
    try:
        if interaction.user.id != ADMIN_ID:
            await interaction.response.send_message("🔴 ¡Solo el administrador puede usar este comando!", ephemeral=True)
            return
        
        if precio <= 0:
            await interaction.response.send_message("🔴 El precio debe ser mayor a cero", ephemeral=True)
            return
        
        global bingo_price
        bingo_price = precio
        
        bingo_data = load_bingo_data()
        bingo_data["price"] = precio
        save_bingo_data(bingo_data)
        
        # Actualizar presencia
        await bot.change_presence(activity=discord.Game(name=f"Bingo | Tasa: {exchange_rate} | Cartón: Bs.{precio}"))
        
        await interaction.response.send_message(f"✅ Precio actualizado a **Bs. {precio:,.2f}**")
    except Exception as e:
        print(f"⚠️ Error en set_bingo_price: {e}")
        await interaction.response.send_message("🔴 Error al actualizar precio", ephemeral=True)

@bot.tree.command(name="agregar_saldo", description="[ADMIN] Agrega saldo a un usuario por ID")
@app_commands.describe(user_id="ID del usuario", cantidad="Cantidad en Bs. a agregar")
async def agregar_saldo(interaction: discord.Interaction, user_id: str, cantidad: float):
    try:
        # Verificar permisos de admin
        if interaction.user.id != ADMIN_ID:
            await interaction.response.send_message(
                "❌ **Acceso denegado:** Solo el administrador puede usar este comando.",
                ephemeral=True
            )
            return
        
        # Cargar datos
        data = load_data()
        
        # Verificar si el usuario existe
        if user_id not in data:
            await interaction.response.send_message(
                f"❌ **Error:** No se encontró una cuenta con el ID `{user_id}`",
                ephemeral=True
            )
            return
        
        # Validar cantidad positiva
        if cantidad <= 0:
            await interaction.response.send_message(
                "❌ **Error:** La cantidad debe ser mayor a cero",
                ephemeral=True
            )
            return
        
        # Actualizar saldo
        data[user_id]["balance"] += cantidad
        save_data(data)
        
        # Intentar notificar al usuario
        try:
            user = await bot.fetch_user(int(user_id))
            embed_dm = discord.Embed(
                title="💵 Saldo Actualizado",
                description=f"Se te ha agregado **Bs. {cantidad:,.2f}**\nNuevo saldo: **Bs. {data[user_id]['balance']:,.2f}**",
                color=discord.Color.green()
            )
            await user.send(embed=embed_dm)
        except (discord.Forbidden, discord.NotFound):
            pass  # No es crítico si no se puede notificar
        
        # Confirmar al admin
        embed = discord.Embed(
            title="✅ Saldo Agregado",
            description=f"Se agregaron **Bs. {cantidad:,.2f}** al usuario con ID `{user_id}`\nNuevo saldo: **Bs. {data[user_id]['balance']:,.2f}**",
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=embed)
        
    except Exception as e:
        print(f"Error en agregar_saldo: {e}")
        await interaction.response.send_message(
            "❌ **Error grave:** No se pudo completar la operación",
            ephemeral=True
        )

# --- INICIAR BOT ---
def setup_keep_alive():
    """Configura el servidor keep-alive para Replit"""
    try:
        from keep_alive import keep_alive
        keep_alive()
        print("🟢 Servidor keep-alive iniciado")
    except ImportError:
        print("🟡 Keep-alive no está configurado")
    except Exception as e:
        print(f"🔴 Error en keep-alive: {e}")

def show_system_info():
    """Muestra información detallada del sistema"""
    import platform
    import sys
    import os
    from datetime import datetime
    
    # Obtener información del sistema
    separator = "="*50
    system_info = [
        "\n" + separator,
        "🟢 INFORMACIÓN DEL SISTEMA",
        f"🕒 Fecha/Hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"💻 Sistema Operativo: {platform.system()} {platform.release()}",
        f"🏷️ Versión del SO: {platform.version()}",
        f"🖥️ Arquitectura: {platform.machine()}",
        f"\n🐍 INFORMACIÓN DE PYTHON",
        f"Versión: {sys.version.split()[0]}",
        f"Implementación: {platform.python_implementation()}",
        f"Compilador: {platform.python_compiler()}",
        f"Ruta ejecutable: {sys.executable}",
        f"\n🌐 INFORMACIÓN DEL ENTORNO",
        f"Directorio actual: {os.getcwd()}",
        f"Plataforma: {platform.platform()}",
        f"Usuario: {os.getenv('USER', 'Desconocido')}",
        f"\n📦 VERSIONES DE PAQUETES",
        f"discord.py: {discord.__version__}",
        separator
    ]
    
    # Mostrar toda la información
    print("\n".join(system_info))

def run_bot():
    """Función principal para ejecutar el bot con manejo de errores"""
    show_system_info()  # Mostrar información del sistema
    setup_keep_alive()
    
    # Intentar conectar/reconectar indefinidamente
    while True:
        try:
            print("🟡 Intentando conectar el bot...")
            bot.run(TOKEN)
            
        except discord.errors.HTTPException as http_error:
            if http_error.status == 429:
                wait_time = 60
                print(f"🔴 Rate limited - Reconectando en {wait_time} segundos...")
                asyncio.sleep(wait_time)
            else:
                wait_time = 30
                print(f"🔴 Error HTTP ({http_error.status}) - Reconectando en {wait_time} segundos...")
                asyncio.sleep(wait_time)
                
        except discord.errors.LoginFailure:
            print("🔴 Error de autenticación - Verifica tu TOKEN")
            break  # Salir del bucle si el token es inválido
            
        except KeyboardInterrupt:
            print("\n🟢 Deteniendo el bot por solicitud del usuario...")
            break  # Salir limpiamente con Ctrl+C
            
        except Exception as general_error:
            wait_time = 15
            print(f"🔴 Error inesperado: {type(general_error).__name__} - {general_error}")
            print(f"🟡 Reconectando en {wait_time} segundos...")
            asyncio.sleep(wait_time)

if __name__ == "__main__":
    run_bot()
    print("🔴 Bot detenido")
    