# Optimizaciones Implementadas

## ✅ Optimización #1: Eliminación de Reintentos Manuales

### Cambio Realizado
Eliminado el loop de reintentos manuales en `transmitter.py` (líneas 130-145 del código original).

### Razón
El nRF24L01+ ya tiene **auto-retransmit** configurado en hardware:
```python
radio.set_retries(5, 15)  # 15 reintentos automáticos en hardware
```

### Resultado
- **Impacto:** Neutro (0% mejora)
- **Razón:** Con 0% de pérdida de paquetes, los reintentos nunca se ejecutaban. Sin embargo, el código es más limpio.

---

## ✅ Optimización #2: Eliminación de Inter-Packet Delay (LA CLAVE 🚀)

### Cambio Realizado
Eliminado el delay de 0.8ms entre paquetes en `constants.py`.

### Código Anterior
```python
INTER_PACKET_DELAY = 0.0008  # 0.8ms entre paquetes
```

### Código Optimizado
```python
INTER_PACKET_DELAY = 0  # Optimizado: 0ms (hardware buffers manejan el flujo)
```

### Resultado
- **Impacto:** **EXITOSO (+110% velocidad)**
- **Velocidad:** De ~15 KiB/s a ~32 KiB/s
- **Razón:** El hardware nRF24 maneja el flujo perfectamente con sus buffers de 3 niveles. El delay era artificial e innecesario.

---

## ❌ Optimización #3: Lectura de ACKs en Batch (FALLIDA)

### Cambio Intentado
Leer ACKs acumulados al final de cada burst en lugar de después de cada paquete.

### Resultado
- **Impacto:** **FRACASO (-98% velocidad)**
- **Velocidad:** Cayó a ~0.6 KiB/s
- **Razón:** El protocolo nRF24 necesita procesar ACKs inmediatamente para confirmar la recepción y liberar buffers. Acumularlos causó retransmisiones masivas y timeouts.
- **Acción:** Revertida.

---

## ❌ Optimización #4: Aumentar Burst Size (FALLIDA)

### Cambio Intentado
Aumentar `BURST_SIZE` de 15 a 30 paquetes.

### Resultado
- **Impacto:** Negativo (-2% velocidad)
- **Razón:** El tamaño de 15 paquetes parece ser el punto óptimo para los buffers del hardware. Aumentarlo no redujo overhead significativo y quizás saturó buffers.
- **Acción:** Revertida a 15.

---

## ✅ Optimización #5: Corrección de Medición en Receptor

### Problema
El receptor reportaba tiempos de ~14s-60s para transferencias que tomaban 3s, resultando en throughputs falsamente bajos (~1-7 KiB/s).

### Cambios Realizados
1. **Inicio de Cronómetro:** Cambiado de "al iniciar modo RX" a "al recibir primer paquete".
2. **Salida Inmediata:** Modificado para salir inmediatamente al recibir todos los paquetes, sin esperar el `IDLE_TIMEOUT` de 10s.

### Resultado
- **Tiempo Reportado:** ~3-4s (correcto)
- **Throughput Reportado:** ~24-32 KiB/s (correcto)
- **Precisión:** Coincide con las métricas del transmisor.

---

## 📊 Resultados Finales

| Métrica | Original | Optimizado | Mejora |
|---------|----------|------------|--------|
| **Tiempo (100KB)** | 6.48s | **3.08s** | **✅ 52% más rápido** |
| **Throughput TX** | 15.43 KiB/s | **32.47 KiB/s** | **✅ +110% (2.1x)** |
| **Throughput RX** | 1.5 KiB/s (erróneo) | **~24-32 KiB/s** | **✅ Medición corregida** |
| **Eficiencia** | 100% | **100%** | ✅ Perfecto |

## 📝 Conclusión
La optimización más efectiva fue simplemente **eliminar los delays artificiales** y dejar que el hardware haga su trabajo. Las optimizaciones lógicas complejas (batching, bursts grandes) resultaron contraproducentes.
