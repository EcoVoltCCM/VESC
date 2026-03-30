import pygame
import serial
import time
from pyvesc import encode
from pyvesc.messages.setters import SetRPM
from pyvesc.messages.base import VESCMessage

# ==========================================
# PARCHE DEFINITIVO PARA EL BUG DE PYVESC
# ==========================================
# 1. Desalojamos la clase original defectuosa del registro interno
if 5 in VESCMessage._msg_registry:
    del VESCMessage._msg_registry[5]

# 2. Registramos nuestra clase corregida
class SetDutyCycleCorregido(metaclass=VESCMessage):
    id = 5  # El ID oficial del VESC para Duty Cycle
    fields = [('duty_cycle', 'i')] # 'i' de Integer, sin multiplicadores automáticos

# ==========================================
# CONFIGURACIÓN DEL SISTEMA
# ==========================================
PUERTO_VESC = 'COM3'
EJE_ACELERADOR = 1

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
        
        # 5. Enviar usando nuestra clase parcheada
        mensaje = SetDutyCycleCorregido(duty_para_vesc)
        conexion_vesc.write(encode(mensaje))
        
        print(f"Multiplicador: {multiplicador_agresivo*100:04.1f}% | Pedal: {porcentaje_acelerador*100:03.0f}% | Mandando VESC: {duty_objetivo*100:04.1f}% Potencia", end='\r')
        
        time.sleep(0.02)

except KeyboardInterrupt:
    print("\n\n[!] PARADA DE EMERGENCIA ACTIVADA.")
    # Parar enviando 0 a nuestra clase y 0 RPM
    conexion_vesc.write(encode(SetDutyCycleCorregido(0)))
    conexion_vesc.write(encode(SetRPM(0)))
    conexion_vesc.close()
    pygame.quit()
    print("[*] Sistema apagado.")