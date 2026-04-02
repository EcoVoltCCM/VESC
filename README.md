# VESC Control Bridge

A Python-based bridge to control a VESC (Vedder Electronic Speed Controller) using a Logitech G920 racing wheel via `pygame` and `pyvesc`.

## Features

- **G920 Integration**: Maps throttle axis to VESC duty cycle.
- **Modern VESC Firmware Support**: Custom message layout for FW 5.x and 6.x.
- **Real-time Telemetry**: Monitor Voltage (V), Current (A), and RPM in real-time.
- **Accurate RPM Calculation**: Configurable Motor Pole Pairs to convert ERPM to Mechanical RPM.
- **Custom Duty Cycle Patch**: Includes a fix for the `pyvesc` library's duty cycle message registration.
- **Safety Measures**: Implements dead zones and emergency stop handling (Ctrl+C).
- **Power Limiting**: Configurable power limits and aggressive throttle mapping.

## Requirements

- Python 3.x
- `pygame`
- `pyserial`
- `pyvesc`

## Configuration

Edit `vesc.py` to adjust:
- `PUERTO_VESC`: Serial port for your VESC (e.g., `COM3` on Windows).
- `EJE_ACELERADOR`: Joystick axis index for the throttle.
- `PARES_POLOS`: Your motor's pole pairs (default 21).
- `LIMITE_POTENCIA`: Maximum duty cycle (0.0 to 1.0).

## Usage

1. Connect your VESC and Logitech G920.
2. Install dependencies:
   ```bash
   pip install pygame pyserial pyvesc
   ```
3. Run the script:
   ```bash
   python vesc.py
   ```

## Emergency Stop

Press **Ctrl+C** in the terminal to immediately stop the motor and close the connection.
