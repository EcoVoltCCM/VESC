import pygame
import serial
import time
from pyvesc import encode, decode, encode_request
from pyvesc.messages.setters import SetRPM
from pyvesc.messages.getters import GetValues
from pyvesc.messages.base import VESCMessage

# ==========================================
# PARCHE DEFINITIVO PARA EL BUG DE PYVESC
# ==========================================
# 1. Desalojamos las clases originales del registro interno
if 4 in VESCMessage._msg_registry:
    del VESCMessage._msg_registry[4]
if 5 in VESCMessage._msg_registry:
    del VESCMessage._msg_registry[5]

# 2. Registramos nuestras clases corregidas (Layout para VESC FW 5.x/6.x)
class SetDutyCycleCorregido(metaclass=VESCMessage):
    id = 5
    fields = [('duty_cycle', 'i')]

class GetValuesCorregido(metaclass=VESCMessage):
    id = 4
    fields = [
        ('temp_fet', 'h', 10),
        ('temp_motor', 'h', 10),
        ('avg_motor_current', 'i', 100),
        ('avg_input_current', 'i', 100),
        ('avg_id', 'i', 100),
        ('avg_iq', 'i', 100),
        ('duty_now', 'h', 1000),
        ('rpm', 'i', 1),
        ('v_in', 'h', 10),
        ('amp_hours', 'i', 10000),
        ('amp_hours_charged', 'i', 10000),
        ('watt_hours', 'i', 10000),
        ('watt_hours_charged', 'i', 10000),
        ('tachometer', 'i', 1),
        ('tachometer_abs', 'i', 1),
        ('mc_fault_code', 'c')
    ]

# ==========================================
# CONFIGURACIÓN DEL SISTEMA
# ==========================================
PUERTO_VESC = 'COM3'
EJE_ACELERADOR = 1

# Configuración del Motor
# El VESC reporta ERPM (RPM Eléctricas). 
# RPM Reales = ERPM / Pares de Polos.
# Si tu motor tiene 21 pares de polos:
PARES_POLOS = 21 

# Límite de potencia (Duty Cycle). Va de 0.0 a 1.0.
LIMITE_POTENCIA = 1  # Puedes ajustar este valor para limitar la potencia máxima que envías al VESC  
# ==========================================

print("Iniciando puente de control VESC...")

try:
    conexion_vesc = serial.Serial(PUERTO_VESC, baudrate=115200, timeout=0.05)
    print(f"[*] VESC conectado exitosamente en {PUERTO_VESC}")
except Exception as e:
    print(f"[!] Error al conectar con el VESC: {e}")
    exit()

pygame.init()
pygame.joystick.init()

if pygame.joystick.get_count() == 0:
    print("[!] No se detectó el Logitech G920.")
    exit()

volante = pygame.joystick.Joystick(0)
volante.init()
print(f"[*] Hardware listo: {volante.get_name()}")
print("-" * 50)
print("SISTEMA ARMADO. Control por DUTY CYCLE (Bug Corregido).")
print("Presiona Ctrl+C en esta ventana para PARO DE EMERGENCIA.")
print("-" * 50)

rpm_actual = 0
v_in = 0.0
i_motor = 0.0

try:
    while True:
        pygame.event.pump()
        
        # 1. Leer eje y mapear (invertido para Logitech)
        valor_crudo = volante.get_axis(EJE_ACELERADOR)
        porcentaje_acelerador = (1.0 - valor_crudo) / 2.0 
        
        # 2. Zona muerta de seguridad
        if porcentaje_acelerador < 0.01:
            porcentaje_acelerador = 0.0
        elif porcentaje_acelerador > 0.95:
            porcentaje_acelerador = 1.0

        # 3. Calcular Duty Cycle con curva agresiva (Tope a la mitad del pedal)
        # Multiplicamos por 2.5 para que al llegar a 0.4 (40%), alcance el 1.0 (máximo)
        multiplicador_agresivo = porcentaje_acelerador * 5
        
        # Le ponemos un techo para que no pase del 100% aunque pises más a fondo
        if multiplicador_agresivo > 0.45:
            multiplicador_agresivo = 0.45

        # Aplicamos tu límite de potencia global
        duty_objetivo = multiplicador_agresivo * LIMITE_POTENCIA
        
        # 4. Escalar a mano para el VESC y forzar el tipo Entero (Integer)
        duty_para_vesc = int(duty_objetivo * 100000)
        
        # 5. Enviar comando de Duty Cycle
        mensaje = SetDutyCycleCorregido(duty_para_vesc)
        conexion_vesc.write(encode(mensaje))
        
        # 6. Solicitar telemetría (RPM, Voltaje, Corriente)
        # Limpiamos el buffer de entrada para no leer datos viejos
        conexion_vesc.reset_input_buffer()
        conexion_vesc.write(encode_request(GetValuesCorregido))
        
        # 7. Leer respuesta (un pequeño delay ayuda a que el VESC responda)
        time.sleep(0.01)
        if conexion_vesc.in_waiting > 0:
            try:
                datos = conexion_vesc.read(conexion_vesc.in_waiting)
                # Intentamos decodificar el paquete. unframe/decode manejará el checksum.
                respuesta, consumido = decode(datos)
                if respuesta:
                    if hasattr(respuesta, 'rpm'):
                        # Convertimos ERPM a RPM Mecánicas
                        rpm_actual = respuesta.rpm / PARES_POLOS
                    if hasattr(respuesta, 'v_in'):
                        v_in = respuesta.v_in
                    if hasattr(respuesta, 'avg_motor_current'):
                        i_motor = respuesta.avg_motor_current
            except Exception:
                pass
        
        print(f"V: {v_in:4.1f}V | A: {i_motor:5.1f}A | RPM: {rpm_actual:6.0f} | Pedal: {porcentaje_acelerador*100:3.0f}% | VESC: {duty_objetivo*100:4.1f}%", end='\r')
        
        time.sleep(0.02)

except KeyboardInterrupt:
    print("\n\n[!] PARADA DE EMERGENCIA ACTIVADA.")
    # Parar enviando 0 a nuestra clase y 0 RPM
    conexion_vesc.write(encode(SetDutyCycleCorregido(0)))
    conexion_vesc.write(encode(SetRPM(0)))
    conexion_vesc.close()
    pygame.quit()
    print("[*] Sistema apagado.")