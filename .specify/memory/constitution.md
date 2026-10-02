<!--
Sync Impact Report
- Versión: 2.0.0 → 2.1.0 (MENOR: el principio V admite una única excepción para la
  contraseña de primer uso de la cuenta inicial `admin`)
- Versión anterior: 1.0.0 → 2.0.0 (MAYOR: el producto pasa de "PresupuestosPro" a "Reservas";
  se redefinen el alcance y los principios II y V)
- Principios:
  - I. Simplicidad ante todo → sin cambios de fondo
  - II. Español de España y euro → II. Idioma y mercado (sin referencias a PDF; el euro
    solo aplica si aparece algún importe)
  - III. Cero alcance fantasma → sin cambios de fondo
  - IV. Verificable por una persona no técnica → ejemplo adaptado a reservas
  - V. Datos del usuario con respeto → "imprescindibles para reservar" en vez de "para el presupuesto"
- Secciones modificadas: Alcance del producto (reescrita para Reservas), Flujo de trabajo
- Secciones eliminadas: ninguna
- Plantillas dependientes: no se modifican (leen la constitución al ejecutarse)
- Resuelto (2.1.0): la cuenta inicial admin/admin de la spec (FR-001) queda permitida como
  excepción explícita del principio V, porque su cambio es obligatorio (FR-002).
-->

# Constitución de Reservas

Reservas es una página web para que los usuarios reserven los espacios de un cliente
(pistas, cabinas, consultas, mesas, puestos, cursos...).

## Core Principles

### I. Simplicidad ante todo

- Entre dos soluciones que cumplen la spec, se elige SIEMPRE la más simple.
- Es una versión 1: NO se añade complejidad "por si acaso" (capas, configuraciones,
  abstracciones o dependencias que hoy no hacen falta).
- Cualquier complejidad extra DEBE justificarse por escrito en el plan.

**Por qué**: lo simple se termina antes, falla menos y se entiende mejor.

### II. Idioma y mercado

- Todo lo que ve el usuario (pantallas, mensajes, errores y emails) DEBE estar en español de España.
- Fechas en formato `dd/mm/aaaa` y horas en formato de 24 h.
- La única moneda es el euro (€). Si aparece algún importe, con formato español: `1.234,56 €`.

**Por qué**: el producto está pensado para clientes y usuarios en España.

### III. Cero alcance fantasma

- NO se implementa ninguna funcionalidad que no esté escrita en la spec.
- Si surge una idea nueva, se PROPONE (se anota para valorarla), pero no se construye.
- Solo entra en el producto después de añadirse a la spec.

**Por qué**: así lo construido coincide con lo acordado.

### IV. Verificable por una persona no técnica

- Cada criterio de éxito DEBE poder comprobarse usando la app, sin leer código.
- Cada criterio describe qué hacer y qué se debe ver (por ejemplo: "al confirmar una
  reserva se muestra su número y llega un email con el resumen").
- Un criterio que no se pueda comprobar así se reescribe antes de construir.

**Por qué**: cualquier persona del proyecto puede confirmar si algo funciona.

### V. Datos del usuario con respeto

- Solo se piden los datos imprescindibles para reservar y gestionar las reservas.
- Cada dato que se pida DEBE tener un uso claro en la spec.
- NUNCA se escriben claves, contraseñas ni secretos en el código.
  Única excepción: la contraseña de primer uso de la cuenta inicial (`admin`), siempre que
  la aplicación obligue a cambiarla antes de permitir cualquier otra acción.

**Por qué**: menos datos significa menos riesgo y más confianza.

## Alcance del producto

- Usuarios: las personas que reservan, el administrador del cliente y el personal de consulta.
- Resultado principal: reservar un espacio en pocos pasos, desde el móvil o el ordenador.
- Lo que no esté en la spec queda fuera de la versión 1 (principio III).

## Flujo de trabajo

- Orden: spec → plan → tareas → implementación.
- Antes de construir, el plan comprueba que cumple los cinco principios.
- Al terminar, se revisan los criterios de éxito usando la app (principio IV).

## Governance

- Esta constitución está por encima de cualquier otra norma o costumbre del proyecto.
- Para cambiarla hay que editar este documento, explicar el motivo y subir la versión:
  - MAYOR: se quita o se redefine un principio.
  - MENOR: se añade un principio o una sección.
  - PARCHE: aclaraciones y correcciones de texto.
- Cada plan y cada revisión comprueban que se cumplen los principios.

**Version**: 2.1.0 | **Ratified**: 2026-10-02 | **Last Amended**: 2026-10-02
