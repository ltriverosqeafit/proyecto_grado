import os
import json
import re
import time
from typing import List, Optional, Dict, Any
from enum import Enum
from typing_extensions import TypedDict
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from pydantic import BaseModel, Field, validator, model_validator
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from langgraph.graph import StateGraph, END

st.set_page_config(
    page_title="Generador de planilla para estimación de precio unitario",
    layout="wide",
)


class clasf_proyecto(str, Enum):
    apto = "apartamento"
    oficina = "oficina"
    consultorio = "consultorio"
    tienda = "tienda"
    restaurante = "restaurante"

class estado_obra(str, Enum):
    obra_civil_remodelacion = "remodelacion o obra civil"
    obra_nueva = "obra nueva"

class capitulo(str, Enum):
    preliminares = "CAP01_PRELIMINARES"
    obra_civil = "CAP02_OBRA_CIVIL_ESTRUCTURA"
    panetes_enchapes = "CAP03_PANETES_ENCHAPES_CIELORASOS"
    pisos = "CAP04_PISOS"
    carpinteria = "CAP05_CARPINTERIA_MUEBLES"
    electrico = "CAP06_ELECTRICO_DATOS"
    hidrosanitario = "CAP07_HIDROSANITARIO"
    aire_acond = "CAP08_AIRE_ACONDICIONADO"
    seguridad = "CAP09_SEGURIDAD_DATOS"
    adicionales = "CAP10_ADICIONALES"

class unidad_medida(str, Enum):
    m2 = "m2"
    ml = "ml"
    un = "un"
    m3 = "m3"
    gl = "gl"
    kg = "kg"

class suministro(str, Enum):
    cliente = "cliente"
    contratista = "contratista"
    por_definir = "por_definir"

class origen_desc(str, Enum):
    explicita = "explicita"
    inferida = "inferida"

class modo_ejecucuion(str, Enum):
    eval = "evaluacion"
    prod = "produccion"

norm_unidad = {
    "metros cuadrados": "m2", "metro cuadrado": "m2",
    "m²": "m2", "mts2": "m2", "mt2": "m2", "M2": "m2",
    "metros lineales": "ml", "metro lineal": "ml",
    "m.l.": "ml", "mts": "ml", "Ml": "ml", "ML": "ml", "m": "ml",
    "metros cubicos": "m3", "metro cubico": "m3",
    "m³": "m3", "M3": "m3",
    "unidad": "un", "unidades": "un", "und": "un",
    "ud": "un", "UND": "un", "Un": "un", "u": "un", "U": "un",
    "global": "gl", "gb": "gl", "GLB": "gl",
    "Global": "gl", "gl": "gl", "GL": "gl", "glb": "gl",
    "glbl": "gl", "Glbl": "gl", "GLBL": "gl",
    "Kg": "kg", "KG": "kg", "kgs": "kg",
    "kilogramo": "kg", "kilogramos": "kg",
    "mm": "un", "MM": "un", "cm": "un", "CM": "un",
    "sem": "un", "SEM": "un",
    "dia": "un", "día": "un", "Día": "un", "DIA": "un", "DÍA": "un",
}

norm_estado = {
    "obra civil o remodelacion": "remodelacion o obra civil",
    "remodelacion o obra civil": "remodelacion o obra civil",
    "remodelacion": "remodelacion o obra civil",
    "adecuacion": "remodelacion o obra civil",
    "adecuación": "remodelacion o obra civil",
    "reforma": "remodelacion o obra civil",
    "intervencion": "remodelacion o obra civil",
    "intervención": "remodelacion o obra civil",
    "renovacion": "remodelacion o obra civil",
    "obra civil": "remodelacion o obra civil",
    "obra nueva": "obra nueva",
    "obra gris": "obra nueva",
    "gris": "obra nueva",
    "entregado en gris": "obra nueva",
    "sin acabados": "obra nueva",
    "construccion nueva": "obra nueva",
    "construccion": "obra nueva",
}

norm_capitulos = {
    "preliminares": "CAP01_PRELIMINARES",
    "preliminares y desmonte": "CAP01_PRELIMINARES",
    "desmonte y desconexiones": "CAP01_PRELIMINARES",
    "desmontes y desconexiones": "CAP01_PRELIMINARES",
    "mamposteria": "CAP02_OBRA_CIVIL_ESTRUCTURA",
    "muros": "CAP02_OBRA_CIVIL_ESTRUCTURA",
    "muros mamposterias panetes enchapes": "CAP02_OBRA_CIVIL_ESTRUCTURA",
    "drywall": "CAP02_OBRA_CIVIL_ESTRUCTURA",
    "drywall y super board": "CAP02_OBRA_CIVIL_ESTRUCTURA",
    "drywall y super board pintura": "CAP02_OBRA_CIVIL_ESTRUCTURA",
    "muros drywall superboard": "CAP02_OBRA_CIVIL_ESTRUCTURA",
    "estructura metalica": "CAP02_OBRA_CIVIL_ESTRUCTURA",
    "estructura": "CAP02_OBRA_CIVIL_ESTRUCTURA",
    "concreto": "CAP02_OBRA_CIVIL_ESTRUCTURA",
    "refuerzos": "CAP02_OBRA_CIVIL_ESTRUCTURA",
    "cubierta": "CAP02_OBRA_CIVIL_ESTRUCTURA",
    "tendido de cubierta": "CAP02_OBRA_CIVIL_ESTRUCTURA",
    "techos": "CAP02_OBRA_CIVIL_ESTRUCTURA",
    "muros y techo": "CAP02_OBRA_CIVIL_ESTRUCTURA",
    "panetes enchapes cielorasos": "CAP03_PANETES_ENCHAPES_CIELORASOS",
    "pañetes enchapes cielorasos": "CAP03_PANETES_ENCHAPES_CIELORASOS",
    "enchapes": "CAP03_PANETES_ENCHAPES_CIELORASOS",
    "enchapes y acabados": "CAP03_PANETES_ENCHAPES_CIELORASOS",
    "cielorasos": "CAP03_PANETES_ENCHAPES_CIELORASOS",
    "recubrimientos en madera": "CAP03_PANETES_ENCHAPES_CIELORASOS",
    "pintura general": "CAP03_PANETES_ENCHAPES_CIELORASOS",
    "pintura": "CAP03_PANETES_ENCHAPES_CIELORASOS",
    "piso": "CAP04_PISOS",
    "pisos": "CAP04_PISOS",
    "pisos y paredes": "CAP04_PISOS",
    "piso microcemento": "CAP04_PISOS",
    "guarda escobas": "CAP04_PISOS",
    "carpinteria": "CAP05_CARPINTERIA_MUEBLES",
    "carpinteria en madera": "CAP05_CARPINTERIA_MUEBLES",
    "carpinterias aluminio cristales": "CAP05_CARPINTERIA_MUEBLES",
    "mesones": "CAP05_CARPINTERIA_MUEBLES",
    "muebles": "CAP05_CARPINTERIA_MUEBLES",
    "mobiliario fijo": "CAP05_CARPINTERIA_MUEBLES",
    "acero inoxidable": "CAP05_CARPINTERIA_MUEBLES",
    "fachada": "CAP05_CARPINTERIA_MUEBLES",
    "instalacion electrica y datos": "CAP06_ELECTRICO_DATOS",
    "instalaciones electricas y datos": "CAP06_ELECTRICO_DATOS",
    "instalacion electrica  y datos": "CAP06_ELECTRICO_DATOS",
    "electrico": "CAP06_ELECTRICO_DATOS",
    "redes electricas": "CAP06_ELECTRICO_DATOS",
    "red normal": "CAP06_ELECTRICO_DATOS",
    "tableros y acometidas": "CAP06_ELECTRICO_DATOS",
    "tablero electrico y rack": "CAP06_ELECTRICO_DATOS",
    "tableros electricos": "CAP06_ELECTRICO_DATOS",
    "iluminacion": "CAP06_ELECTRICO_DATOS",
    "iluminacion especial": "CAP06_ELECTRICO_DATOS",
    "instalacion de datos": "CAP06_ELECTRICO_DATOS",
    "sistema de comunicaciones": "CAP06_ELECTRICO_DATOS",
    "instalaciones datos sonido cctv": "CAP06_ELECTRICO_DATOS",
    "cableado de acometidas": "CAP06_ELECTRICO_DATOS",
    "diseño electrico y datos": "CAP06_ELECTRICO_DATOS",
    "especiales": "CAP06_ELECTRICO_DATOS",
    "instalaciones hidrosanitarias": "CAP07_HIDROSANITARIO",
    "hidraulicos barra": "CAP07_HIDROSANITARIO",
    "hidrosanitarios": "CAP07_HIDROSANITARIO",
    "hidrosanitario y gas": "CAP07_HIDROSANITARIO",
    "redes hidrosanitarias": "CAP07_HIDROSANITARIO",
    "instalaciones hidraulicas": "CAP07_HIDROSANITARIO",
    "instalaciones sanitarias": "CAP07_HIDROSANITARIO",
    "aparatos sanitarios griferias y accesorios": "CAP07_HIDROSANITARIO",
    "aparatos sanitarios griferias accesorios": "CAP07_HIDROSANITARIO",
    "equipos y accesorios de bano": "CAP07_HIDROSANITARIO",
    "diseño hidrosanitario": "CAP07_HIDROSANITARIO",
    "aire acondicionado": "CAP08_AIRE_ACONDICIONADO",
    "ductos": "CAP08_AIRE_ACONDICIONADO",
    "red de detencion de incendios": "CAP09_SEGURIDAD_DATOS",
    "rci": "CAP09_SEGURIDAD_DATOS",
    "red contra incendios": "CAP09_SEGURIDAD_DATOS",
    "red de incendio": "CAP09_SEGURIDAD_DATOS",
    "diseño rci deteccion y especiales": "CAP09_SEGURIDAD_DATOS",
    "diseño deteccion": "CAP09_SEGURIDAD_DATOS",
    "cctv": "CAP09_SEGURIDAD_DATOS",
    "control acceso": "CAP09_SEGURIDAD_DATOS",
    "sistema intrusion": "CAP09_SEGURIDAD_DATOS",
    "cctv y datos": "CAP09_SEGURIDAD_DATOS",
    "instalaciones de cctv": "CAP09_SEGURIDAD_DATOS",
    "protecciones": "CAP09_SEGURIDAD_DATOS",
    "otros": "CAP10_ADICIONALES",
    "otros items": "CAP10_ADICIONALES",
    "adicionales": "CAP10_ADICIONALES",
    "ornamentacion": "CAP10_ADICIONALES",
    "bodega": "CAP10_ADICIONALES",
    "bodega interna": "CAP10_ADICIONALES",
    "equipos especiales": "CAP10_ADICIONALES",
    "equipos": "CAP10_ADICIONALES",
    "aseo y entrega": "CAP10_ADICIONALES",
    "aseo y entrega de obra": "CAP10_ADICIONALES",
    "gastos administrativos": "CAP10_ADICIONALES",
    "personal exigido": "CAP10_ADICIONALES",
}

def norm_capitulos_fn(nombre):
    return norm_capitulos.get(norm_texto(nombre), "NO_MAPEADO")

def norm_texto(v: str) -> str:
    v = v.lower().strip()
    for orig, dest in {"á":"a","é":"e","í":"i","ó":"o","ú":"u","ñ":"n","-":" ","_":" "}.items():
        v = v.replace(orig, dest)
    return " ".join(v.split())

class actividad(BaseModel):
    capitulo:    capitulo
    descripcion: str
    referencia:  Optional[str] = None
    unidad:      unidad_medida
    cantidad:    float
    suministro:  suministro
    origen:      origen_desc = origen_desc.explicita
    observacion: Optional[str] = None

    @validator("unidad", pre=True)
    def normalizar_unidad(cls, v):
        if isinstance(v, str):
            val = v.strip()
            if val in norm_unidad:
                return norm_unidad[val]
            if val in [e.value for e in unidad_medida]:
                return val
            raise ValueError(f"unidad '{v}' no válida")
        return v

    @validator("descripcion")
    def validar_descripcion(cls, v):
        v = v.strip()
        if len(v) < 5:
            raise ValueError("descripcion muy corta")
        return v

    @validator("referencia")
    def validar_referencia(cls, v):
        if v is not None:
            v = v.strip().upper()
            if len(v) < 3:
                raise ValueError("referencia muy corta")
        return v

    @validator("cantidad")
    def validar_cantidad(cls, v):
        if v is None:
            raise ValueError("cantidad obligatoria")
        if v <= 0:
            raise ValueError("cantidad debe ser mayor a cero")
        return round(v, 2)


class espacio(BaseModel):
    nombre:      str
    area_m2:     Optional[float] = None
    actividades: List[actividad] = Field(default_factory=list)

    @validator("nombre")
    def normalizar_nombre(cls, valor):
        return norm_texto(valor).replace(" ", "_")

    @validator("area_m2")
    def area_valida(cls, valor):
        if valor is not None and valor <= 0:
            raise ValueError("area debe ser mayor a cero")
        return round(valor, 2) if valor else valor

    @validator("actividades")
    def act_valida(cls, actividades, values):
        area = values.get("area_m2")
        if area:
            for act in actividades:
                if act.unidad == unidad_medida.m2 and act.cantidad > area * 5:
                    raise ValueError(
                        f"cantidad sospechosa: {act.descripcion} "
                        f"tiene {act.cantidad}m2 en espacio de {area}m2"
                    )
        return actividades


class proyecto(BaseModel):
    tipo: clasf_proyecto
    estado: estado_obra
    area_total: Optional[float] = None
    altura_entrepiso: float = 2.40
    espacios: List[espacio] = Field(default_factory=list)
    alertas: List[str] = Field(default_factory=list)

    @validator("estado", pre=True)
    def normalizar_estado(cls, v):
        return norm_estado.get(norm_texto(str(v)), str(v))

    @validator("area_total")
    def validar_area_total(cls, v):
        if v is not None and v <= 0:
            raise ValueError("area total no es correcta")
        return round(v, 2) if v else v

    @validator("altura_entrepiso")
    def validar_altura(cls, v):
        if v <= 0 or v > 6.0:
            raise ValueError("altura de entrepiso no es correcta")
        return round(v, 2)

    @validator("espacios")
    def validar_espacios(cls, v):
        if not v:
            return v
        nombres = [e.nombre for e in v]
        if len(nombres) != len(set(nombres)):
            dups = {n for n in nombres if nombres.count(n) > 1}
            raise ValueError(f"espacios duplicados: {dups}")
        return v

    @model_validator(mode="after")
    def validaciones_cruzadas(self):
        if self.estado == estado_obra.obra_nueva:
            for esp in self.espacios:
                caps = [a.capitulo for a in esp.actividades]
                if capitulo.preliminares in caps:
                    self.alertas.append(
                        f"alerta: {esp.nombre} tiene demoliciones "
                        f"pero el estado es obra nueva"
                    )
        if self.area_total is None:
            areas = [e.area_m2 for e in self.espacios if e.area_m2]
            if areas:
                self.area_total = round(sum(areas), 2)
                self.alertas.append(f"supuesto: area total = {self.area_total}m2")
        if self.area_total:
            areas = [e.area_m2 for e in self.espacios if e.area_m2]
            if areas:
                suma = round(sum(areas), 2)
                if abs(self.area_total - suma) > self.area_total * 0.10:
                    self.alertas.append(
                        f"alerta: area declarada ({self.area_total}m2) "
                        f"difiere >10% de suma espacios ({suma}m2)"
                    )
        for esp in self.espacios:
            if esp.area_m2 is None:
                self.alertas.append(f"pregunta: cuantos m2 tiene {esp.nombre}?")
        return self

    @property
    def area_calculada(self):
        return round(sum(e.area_m2 for e in self.espacios if e.area_m2), 2)

    @property
    def tiene_preguntas(self):
        return any("pregunta:" in a for a in self.alertas)

    @property
    def preguntas_pendientes(self):
        return [a for a in self.alertas if "pregunta:" in a]

    @property
    def supuestos(self):
        return [a for a in self.alertas if "supuesto:" in a]

    @property
    def inconsistencias(self):
        return [a for a in self.alertas if "alerta:" in a]

    @property
    def actividades_planas(self):
        return [
            {
                "espacio": esp.nombre,
                "capitulo": act.capitulo.value,
                "descripcion": act.descripcion,
                "referencia": act.referencia,
                "unidad": act.unidad.value,
                "cantidad": act.cantidad,
                "suministro": act.suministro.value,
                "origen": act.origen.value,
            }
            for esp in self.espacios
            for act in esp.actividades
        ]

    @property
    def actividades_cliente(self):
        return [
            {
                "espacio": esp.nombre,
                "actividad": act.descripcion,
                "referencia": act.referencia,
                "cantidad": act.cantidad,
                "unidad": act.unidad.value,
            }
            for esp in self.espacios
            for act in esp.actividades
            if act.suministro == suministro.cliente
        ]

    @property
    def resumen_capitulos(self):
        res = {}
        for esp in self.espacios:
            for act in esp.actividades:
                cap = act.capitulo.value
                if cap not in res:
                    res[cap] = {"n": 0, "espacios": []}
                res[cap]["n"] += 1
                if esp.nombre not in res[cap]["espacios"]:
                    res[cap]["espacios"].append(esp.nombre)
        return res

    def planilla_texto(self):
        lineas = [
            f"proyecto: {self.tipo.value.upper()} | {self.estado.value.upper()}",
            f"area: {self.area_total}m2 | altura: {self.altura_entrepiso}m",
            "=" * 60,
        ]
        for esp in self.espacios:
            lineas.append(f"\n{esp.nombre.upper()} ({esp.area_m2}m2)")
            cap_actual = None
            for act in esp.actividades:
                if act.capitulo != cap_actual:
                    lineas.append(f"  [{act.capitulo.value}]")
                    cap_actual = act.capitulo
                tag = {"cliente": "cliente", "contratista": "contratista",
                       "por_definir": "sin definir"}[act.suministro.value]
                lineas.append(
                    f"    {act.descripcion:<45} "
                    f"{act.cantidad:>7.2f} {act.unidad.value:<4} [{tag}]"
                )
        if self.alertas:
            lineas.append("alertas:")
            lineas.extend(f"  {a}" for a in self.alertas)
        return "\n".join(lineas)

class AgentState(TypedDict):
    texto: str
    modo: str
    caso_id: Optional[str]
    output_raw: Optional[Dict[str, Any]]
    proyecto: Optional[Dict[str, Any]]
    schema_ok: bool
    intentos: int
    error_pydantic: Optional[str]
    bloqueado: bool
    trajectory: List[Dict[str, Any]]
    modelo_llm: str
    latencia_ms: Optional[float]

def init_state(texto, modo=modo_ejecucuion.eval, caso_id=None, modelo_llm="gpt-4o-mini"):
    return AgentState(
        texto=texto, modo=modo, caso_id=caso_id,
        output_raw=None, proyecto=None, schema_ok=False,
        intentos=0, error_pydantic=None, bloqueado=False,
        trajectory=[], modelo_llm=modelo_llm, latencia_ms=None,
    )

def log_paso(state, componente, decision, resultado, detalle):
    state["trajectory"].append({
        "componente": componente,
        "decision": decision,
        "resultado": resultado,
        "detalle": detalle,
    })

def limpiar_json(texto_raw):
    texto = texto_raw.strip()
    if texto.startswith("```"):
        lineas = texto.split("\n")
        texto = "\n".join(l for l in lineas if not l.startswith("```")).strip()
    try:
        return json.loads(texto), None
    except json.JSONDecodeError as e:
        return None, str(e)

def nodo_reasoning(state, llm):
    msgs = [SystemMessage(content=SYSTEM_PROMPT), HumanMessage(content=state["texto"])]
    if state["error_pydantic"]:
        msgs.append(HumanMessage(content=f"Tu respuesta anterior tuvo este error:\n{state['error_pydantic']}\nCorrige"))
    t0 = time.time()
    respuesta = llm.invoke(msgs)
    latencia = round((time.time() - t0) * 1000, 2)
    output_raw, error_parse = limpiar_json(respuesta.content)
    log_paso(state, "reasoning", "extraer e inferir actividades",
        "ok" if output_raw else "fallo",
        {"intento": state["intentos"]+1, "error_parse": error_parse, "latencia_ms": latencia})
    state["output_raw"] = output_raw
    state["latencia_ms"] = latencia
    state["intentos"] += 1
    return state

def nodo_validador(state):
    if state["output_raw"] is None:
        state["schema_ok"] = False
        state["error_pydantic"] = "el LLM no devolvió un JSON"
        log_paso(state, "validador", "validar schema", "fallo", {"error": state["error_pydantic"]})
        return state
    try:
        proy = proyecto(**state["output_raw"])
        ok, error = True, None
    except Exception as e:
        proy, ok, error = None, False, str(e)
    log_paso(state, "validador", "validar schema",
        "ok" if ok else "fallo",
        {"intento": state["intentos"], "schema_ok": ok, "error": error})
    state["schema_ok"] = ok
    state["error_pydantic"] = error
    state["proyecto"] = proy.model_dump(mode="json") if ok and proy else None
    return state

def nodo_preguntas(state):
    if not state["proyecto"]:
        return state
    proy = proyecto.model_validate(state["proyecto"])
    bloqueantes = [a for a in proy.alertas if "pregunta_bloqueante:" in a]
    bloqueado = len(bloqueantes) > 0 and state["modo"] == modo_ejecucuion.prod
    log_paso(state, "preguntas", "generar preguntas",
        "pregunta" if bloqueantes else "ok",
        {"bloqueantes": bloqueantes, "supuestos": proy.supuestos})
    state["bloqueado"] = bloqueado
    return state

def routing(state):
    if state["schema_ok"]:
        return "preguntas"
    if state["intentos"] < max_intentos:
        return "reasoning"
    if state["modo"] != modo_ejecucuion.eval:
        raw = state.get("output_raw") or {}
        raw.setdefault("alertas", [])
        raw["alertas"].append(f"alerta: output incompleto — {state['error_pydantic']}")
        state["proyecto"] = raw
    return "fin"

def crear_grafo(llm):
    grafo = StateGraph(AgentState)
    grafo.add_node("reasoning", lambda s: nodo_reasoning(s, llm))
    grafo.add_node("validador", nodo_validador)
    grafo.add_node("preguntas", nodo_preguntas)
    grafo.set_entry_point("reasoning")
    grafo.add_edge("reasoning", "validador")
    grafo.add_conditional_edges("validador", routing,
        {"reasoning": "reasoning", "preguntas": "preguntas", "fin": END})
    grafo.add_edge("preguntas", END)
    return grafo.compile()

def run_agente(texto, llm):
    agente = crear_grafo(llm)
    nombre_modelo = llm.model_name if hasattr(llm, "model_name") else str(llm)
    state = init_state(texto=texto, modelo_llm=nombre_modelo)
    return agente.invoke(state)

SYSTEM_PROMPT = """
Eres un interventor de obra con 15 años de experiencia en proyectos de adecuación,
remodelación y construcción de espacios comerciales y de oficinas en Colombia.

La funcion que debes realizar es leer la descripción de un proyecto constructivo y generar una planilla
de estimación de costos APU organizada por capitulos y actividades.

Debes hacer dos cosas:
1. EXTRAER las actividades que el contratista describe explícitamente en el texto.
2. INFERIR las actividades que aplican según el tipo de proyecto y estado de la obra,
   aunque el contratista no las mencione.


Formato de la respuesta:
Responde unicamente con un JSON válido con esta estructura exacta:

{
  "tipo": "<apartamento|oficina|clinica|consultorio|tienda|restaurante>",
  "estado": "<remodelacion o obra civil|obra nueva>",
  "area_total": <número o null>,
  "altura_entrepiso": <número, default 2.40>,
  "espacios": [
    {
      "nombre": "<nombre_sin_tildes_ni_espacios>",
      "area_m2": <número o null>,
      "actividades": [
        {
          "capitulo": "<CAP01_PRELIMINARES|CAP02_OBRA_CIVIL_ESTRUCTURA|CAP03_PANETES_ENCHAPES_CIELORASOS|CAP04_PISOS|CAP05_CARPINTERIA_MUEBLES|CAP06_ELECTRICO_DATOS|CAP07_HIDROSANITARIO|CAP08_AIRE_ACONDICIONADO|CAP09_SEGURIDAD_DATOS|CAP10_ADICIONALES>",
          "descripcion": "<descripción técnica de la actividad>",
          "referencia": "<referencia del material o null>",
          "unidad": "<m2|ml|un|m3|gl>",
          "cantidad": <número mayor a cero>,
          "suministro": "<contratista|cliente|por_definir>",
          "origen": "<explicita|inferida>",
          "observacion": "<supuesto aplicado o null>"
        }
      ]
    }
  ],
  "alertas": []
}

Ejemplos:

Ejemplo 1: el tipo de proyecto es un consultorio, con estado de la obra en remodelacion y un area total de 108 m2:
Este es el detalle y completitud esperado para un proyecto de obra civil o remodelacion.

{
  "tipo": "consultorio",
  "estado": "remodelacion o obra civil",
  "area_total": 108,
  "altura_entrepiso": 2.40,
  "espacios": [
    {
      "nombre": "area_general",
      "area_m2": 108,
      "actividades": [
        {"capitulo":"CAP01_PRELIMINARES","descripcion":"Demolicion de muros de drywall","referencia":null,"unidad":"m2","cantidad":36,"suministro":"contratista","origen":"explicita","observacion":null},
        {"capitulo":"CAP01_PRELIMINARES","descripcion":"Desmonte de piso existente","referencia":null,"unidad":"m2","cantidad":120,"suministro":"contratista","origen":"inferida","observacion":"supuesto: desmonte previo a piso nuevo"},
        {"capitulo":"CAP01_PRELIMINARES","descripcion":"Desmonte de cieloraso existente","referencia":null,"unidad":"m2","cantidad":120,"suministro":"contratista","origen":"inferida","observacion":null},
        {"capitulo":"CAP01_PRELIMINARES","descripcion":"Desmonte de redes electricas y de datos existentes","referencia":null,"unidad":"gl","cantidad":1,"suministro":"contratista","origen":"inferida","observacion":null},
        {"capitulo":"CAP01_PRELIMINARES","descripcion":"Regata en muros y pisos","referencia":null,"unidad":"ml","cantidad":28,"suministro":"contratista","origen":"inferida","observacion":null},
        {"capitulo":"CAP01_PRELIMINARES","descripcion":"Material de proteccion","referencia":null,"unidad":"gl","cantidad":1,"suministro":"contratista","origen":"inferida","observacion":null},
        {"capitulo":"CAP01_PRELIMINARES","descripcion":"Retiro de escombros","referencia":null,"unidad":"gl","cantidad":1,"suministro":"contratista","origen":"inferida","observacion":null},
        {"capitulo":"CAP02_OBRA_CIVIL_ESTRUCTURA","descripcion":"Muro drywall doble cara con frescasa","referencia":null,"unidad":"m2","cantidad":71,"suministro":"contratista","origen":"explicita","observacion":null},
        {"capitulo":"CAP02_OBRA_CIVIL_ESTRUCTURA","descripcion":"Muro superboard","referencia":null,"unidad":"m2","cantidad":25,"suministro":"contratista","origen":"explicita","observacion":null},
        {"capitulo":"CAP02_OBRA_CIVIL_ESTRUCTURA","descripcion":"Dinteles en drywall","referencia":null,"unidad":"ml","cantidad":16,"suministro":"contratista","origen":"inferida","observacion":null},
        {"capitulo":"CAP03_PANETES_ENCHAPES_CIELORASOS","descripcion":"Resanes de regatas en muros y pisos","referencia":null,"unidad":"ml","cantidad":25,"suministro":"contratista","origen":"inferida","observacion":null},
        {"capitulo":"CAP03_PANETES_ENCHAPES_CIELORASOS","descripcion":"Instalacion enchape muro porcelanato Amalfi Inout 100x100 Beige","referencia":"Amalfi Inout 100x100 Beige","unidad":"m2","cantidad":28,"suministro":"contratista","origen":"explicita","observacion":null},
        {"capitulo":"CAP03_PANETES_ENCHAPES_CIELORASOS","descripcion":"Cieloraso en drywall","referencia":null,"unidad":"m2","cantidad":120,"suministro":"contratista","origen":"explicita","observacion":null},
        {"capitulo":"CAP03_PANETES_ENCHAPES_CIELORASOS","descripcion":"Tapas de inspeccion cieloraso 60x60 tipo push","referencia":null,"unidad":"un","cantidad":4,"suministro":"contratista","origen":"inferida","observacion":"supuesto: tapas de inspeccion para cieloraso drywall"},
        {"capitulo":"CAP03_PANETES_ENCHAPES_CIELORASOS","descripcion":"Dilataciones en Z cieloraso","referencia":null,"unidad":"ml","cantidad":48,"suministro":"contratista","origen":"inferida","observacion":null},
        {"capitulo":"CAP03_PANETES_ENCHAPES_CIELORASOS","descripcion":"Pintura viniilica muros","referencia":null,"unidad":"m2","cantidad":184,"suministro":"contratista","origen":"inferida","observacion":null},
        {"capitulo":"CAP03_PANETES_ENCHAPES_CIELORASOS","descripcion":"Estuco muros","referencia":null,"unidad":"m2","cantidad":101,"suministro":"contratista","origen":"inferida","observacion":null},
        {"capitulo":"CAP04_PISOS","descripcion":"Alistado de piso","referencia":null,"unidad":"m2","cantidad":108,"suministro":"contratista","origen":"inferida","observacion":"supuesto: alistado previo a piso nuevo"},
        {"capitulo":"CAP04_PISOS","descripcion":"Instalacion enchape piso porcelanato Neeko Inout 60x120 Blanco","referencia":"Neeko Inout 60x120 Blanco","unidad":"m2","cantidad":108,"suministro":"contratista","origen":"explicita","observacion":null},
        {"capitulo":"CAP04_PISOS","descripcion":"Guardaescoba aglomerado segun referencia","referencia":null,"unidad":"ml","cantidad":42,"suministro":"contratista","origen":"inferida","observacion":null},
        {"capitulo":"CAP05_CARPINTERIA_MUEBLES","descripcion":"Puerta corrediza vidrio laminado 3+3 perfil 1101","referencia":null,"unidad":"un","cantidad":2,"suministro":"contratista","origen":"explicita","observacion":null},
        {"capitulo":"CAP05_CARPINTERIA_MUEBLES","descripcion":"Puerta batiente vidrio laminado 3+3 cerradura llave llave","referencia":null,"unidad":"un","cantidad":4,"suministro":"contratista","origen":"explicita","observacion":null},
        {"capitulo":"CAP06_ELECTRICO_DATOS","descripcion":"Salida para luminaria colgante campana incluye suministro","referencia":null,"unidad":"un","cantidad":6,"suministro":"contratista","origen":"explicita","observacion":null},
        {"capitulo":"CAP06_ELECTRICO_DATOS","descripcion":"Salida para tomacorriente red normal doble Nema 5-15R Leviton","referencia":"Leviton Nema 5-15R","unidad":"un","cantidad":18,"suministro":"contratista","origen":"explicita","observacion":null},
        {"capitulo":"CAP06_ELECTRICO_DATOS","descripcion":"Salida para punto de datos CAT 6A","referencia":null,"unidad":"un","cantidad":12,"suministro":"contratista","origen":"explicita","observacion":null},
        {"capitulo":"CAP06_ELECTRICO_DATOS","descripcion":"Patch panel CAT 6A 24 puertos","referencia":null,"unidad":"un","cantidad":1,"suministro":"contratista","origen":"explicita","observacion":null},
        {"capitulo":"CAP06_ELECTRICO_DATOS","descripcion":"Acondicionamiento tablero electrico existente","referencia":null,"unidad":"gl","cantidad":1,"suministro":"contratista","origen":"explicita","observacion":null}
      ]
    }
  ],
  "alertas": ["pregunta: tiene referencia de enchape de piso?", "supuesto: altura entrepiso 2.40m, confirmar"]
}

Ejemplo 2: el tipo de proyecto es una tienda, con estado en obra nueva y un area total de 80m2:
Este es el detalle y completitud esperado para un proyecto de obra civil o remodelacion.

{
  "tipo": "tienda",
  "estado": "obra nueva",
  "area_total": 80,
  "altura_entrepiso": 2.40,
  "espacios": [
    {
      "nombre": "area_de_ventas",
      "area_m2": 62,
      "actividades": [
        {"capitulo":"CAP01_PRELIMINARES","descripcion":"Localizacion y replanteo","referencia":null,"unidad":"m2","cantidad":62,"suministro":"contratista","origen":"inferida","observacion":null},
        {"capitulo":"CAP01_PRELIMINARES","descripcion":"Desconexion de puntos electricos salidas e iluminacion existentes","referencia":null,"unidad":"gl","cantidad":1,"suministro":"contratista","origen":"inferida","observacion":"supuesto: local comercial con instalaciones anteriores"},
        {"capitulo":"CAP01_PRELIMINARES","descripcion":"Desconexion de puntos hidrosanitarios existentes","referencia":null,"unidad":"gl","cantidad":1,"suministro":"contratista","origen":"inferida","observacion":null},
        {"capitulo":"CAP02_OBRA_CIVIL_ESTRUCTURA","descripcion":"Muro una cara superboard 8mm con pintura acryltex blanca","referencia":null,"unidad":"m2","cantidad":11,"suministro":"contratista","origen":"explicita","observacion":null},
        {"capitulo":"CAP02_OBRA_CIVIL_ESTRUCTURA","descripcion":"Muro doble cara superboard 8mm con pintura acryltex blanca","referencia":null,"unidad":"m2","cantidad":30,"suministro":"contratista","origen":"explicita","observacion":null},
        {"capitulo":"CAP02_OBRA_CIVIL_ESTRUCTURA","descripcion":"Pintura acryltex blanca a 3 manos muros","referencia":"Acryltex blanca","unidad":"m2","cantidad":58,"suministro":"contratista","origen":"inferida","observacion":null},
        {"capitulo":"CAP03_PANETES_ENCHAPES_CIELORASOS","descripcion":"Cieloraso drywall con pintura texturizada Wax Yellow Sapolin","referencia":"Wax Yellow 2015P Sapolin","unidad":"m2","cantidad":62,"suministro":"contratista","origen":"explicita","observacion":null},
        {"capitulo":"CAP03_PANETES_ENCHAPES_CIELORASOS","descripcion":"Tapas de inspeccion cieloraso 60x60 incluye marco aluminio","referencia":null,"unidad":"un","cantidad":2,"suministro":"contratista","origen":"inferida","observacion":"supuesto: tapas de inspeccion para cieloraso drywall"},
        {"capitulo":"CAP03_PANETES_ENCHAPES_CIELORASOS","descripcion":"Piedra sinterizada pared Belvedere Black Mate Gramar","referencia":"Belvedere Black Mate Gramar","unidad":"m2","cantidad":21,"suministro":"contratista","origen":"explicita","observacion":null},
        {"capitulo":"CAP04_PISOS","descripcion":"Afinado de piso","referencia":null,"unidad":"m2","cantidad":62,"suministro":"contratista","origen":"inferida","observacion":null},
        {"capitulo":"CAP04_PISOS","descripcion":"Enchape piso porcelanato Chateau White 120x60 Attmosferas boquilla epoxica","referencia":"Chateau White 120x60 Attmosferas","unidad":"m2","cantidad":62,"suministro":"contratista","origen":"explicita","observacion":null},
        {"capitulo":"CAP04_PISOS","descripcion":"Guardaescoba media cana fundida en sitio con pintura epoxica blanca","referencia":null,"unidad":"ml","cantidad":33,"suministro":"contratista","origen":"inferida","observacion":null},
        {"capitulo":"CAP06_ELECTRICO_DATOS","descripcion":"Salida para lampara lineal","referencia":null,"unidad":"un","cantidad":4,"suministro":"contratista","origen":"explicita","observacion":null},
        {"capitulo":"CAP06_ELECTRICO_DATOS","descripcion":"Salida para tomacorriente doble polo a tierra 15A Leviton","referencia":"Leviton 5262-W","unidad":"un","cantidad":14,"suministro":"contratista","origen":"explicita","observacion":null},
        {"capitulo":"CAP06_ELECTRICO_DATOS","descripcion":"Salida para datos doble CAT 6","referencia":null,"unidad":"un","cantidad":4,"suministro":"contratista","origen":"explicita","observacion":null},
        {"capitulo":"CAP07_HIDROSANITARIO","descripcion":"Punto hidraulico agua fria PVC-P 1/2 Pavco","referencia":"Pavco 1/2\"","unidad":"un","cantidad":6,"suministro":"contratista","origen":"explicita","observacion":null},
        {"capitulo":"CAP07_HIDROSANITARIO","descripcion":"Salida sanitaria PVC 2 pulgadas","referencia":null,"unidad":"un","cantidad":4,"suministro":"contratista","origen":"explicita","observacion":null},
        {"capitulo":"CAP07_HIDROSANITARIO","descripcion":"Instalacion caja lavadora incluye sellado y hermeticidad","referencia":null,"unidad":"un","cantidad":4,"suministro":"contratista","origen":"explicita","observacion":null},
        {"capitulo":"CAP07_HIDROSANITARIO","descripcion":"Instalacion coldrink triple incluye acoples y mangueras","referencia":null,"unidad":"un","cantidad":1,"suministro":"contratista","origen":"explicita","observacion":null},
        {"capitulo":"CAP09_SEGURIDAD_DATOS","descripcion":"Detector de temperatura red de incendios","referencia":null,"unidad":"un","cantidad":2,"suministro":"contratista","origen":"explicita","observacion":null},
        {"capitulo":"CAP09_SEGURIDAD_DATOS","descripcion":"Rociador automatico cobertura extendida","referencia":null,"unidad":"un","cantidad":4,"suministro":"contratista","origen":"explicita","observacion":null},
        {"capitulo":"CAP09_SEGURIDAD_DATOS","descripcion":"Camara CCTV incluye cableado y accesorios","referencia":null,"unidad":"un","cantidad":3,"suministro":"contratista","origen":"explicita","observacion":null}
      ]
    },
    {
      "nombre": "bodega",
      "area_m2": 18,
      "actividades": [
        {"capitulo":"CAP04_PISOS","descripcion":"Afinado de piso bodega","referencia":null,"unidad":"m2","cantidad":18,"suministro":"contratista","origen":"inferida","observacion":null},
        {"capitulo":"CAP10_ADICIONALES","descripcion":"Adecuacion bodega interna","referencia":null,"unidad":"gl","cantidad":1,"suministro":"contratista","origen":"explicita","observacion":null}
      ]
    }
  ],
  "alertas": ["pregunta: los sanitarios los suministra el cliente o el contratista?", "supuesto: altura entrepiso 2.40m, confirmar"]
}

Clasificacion de los capitulos APU:

CAP01_PRELIMINARES
  incluye: todo lo que se desmonta, demolece o retira antes de construir, incluye protección, localización y retiro de escombros.
  Ejemplos: demolición muros drywall, desmonte piso existente, desmonte cieloraso, desmonte tablero eléctrico, desconexión puntos eléctricos e hidrosanitarios,
  regatas en muros y pisos, retiro escombros, material protección.

CAP02_OBRA_CIVIL_ESTRUCTURA
  incluye: construcción de muros nuevos, estructura metálica, mampostería, concreto, cubierta y refuerzos estructurales.
  Ejemplos: muro drywall doble cara con frescasa, muro drywall una cara, muro superboard, muro mampostería, dinteles drywall, estructura metálica
  sobrepiso, cubierta vidrio templado, frescasa muros.

CAP03_PANETES_ENCHAPES_CIELORASOS
  incluye: acabados de muros y techos — pañetes, enchapes, cielorasos, pintura, recubrimientos y elementos decorativos de techo.
  Ejemplos: cieloraso drywall, cieloraso XSound, enchape muro porcelanato, enchape muro cerámica, pintura vinílica, estuco, resanes regatas,
  dilataciones en Z cieloraso, nichos de luz, cortineros drywall, tapas inspección cieloraso 60x60, palillaje melamina techo.

CAP04_PISOS
  incluye: instalación de pisos, alistados, guardaescobas y mediacañas.
  Ejemplos: instalación porcelanato 60x120, instalación cerámica, piso microcemento, alistado de piso, fundida contrapiso, guardaescoba aglomerado, media caña resina,
  guardaescoba metálico, perfil metálico piso.

CAP05_CARPINTERIA_MUEBLES
  incluye: muebles, mesones, carpintería en madera, divisiones en vidrio,fachadas en vidrio/aluminio y acero inoxidable.
  Ejemplos: mueble melamina, mesón piedra sinterizada, mesón acero inoxidable, división vidrio aluminio, puerta corredera vidrio, puerta batiente vidrio,
  fachada vidrio templado, poceta acero inoxidable, carpintería madera.

CAP06_ELECTRICO_DATOS
  incluye: todo lo eléctrico — salidas de iluminación, tomacorrientes, tableros, acometidas, cableado, datos, voz y suministro de luminarias.
  Ejemplos: salida luminaria colgante, salida bala recesada, tomacorriente normal, tomacorriente regulado, tomacorriente GFCI, tablero eléctrico
  trifásico, breakers, acometida, punto de datos CAT6A, patch panel, certificación RETIE, instalación luminaria con suministro.

CAP07_HIDROSANITARIO
  incluye: redes de agua fría, caliente y filtrada, desagües, aparatos sanitarios, griferías, gas y equipos de agua.
  Ejemplos: punto hidráulico agua fría, punto hidráulico agua caliente,
  punto agua filtrada, salida sanitaria 2", salida sanitaria 4", tubería PVC, registro bola, lavamanos, sanitario, grifería, calentador agua, filtro agua,
  punto de gas, coldrink, caja lavadora, trampa grasas.

CAP08_AIRE_ACONDICIONADO
  incluye: ductos, rejillas, difusores, termostatos y equipos de AA.
  Ejemplos: ducto flexible rejilla inyección, ducto flexible rejilla extracción,
  termostato, espiroducto, rejilla lineal, reinstalación rejillas AA.

CAP09_SEGURIDAD_DATOS
  incluye: deteccion de incendios, rociadores, CCTV, control de acceso, sistema de intrusión y red contra incendios.
  Ejemplos: detector de temperatura, rociador automático, estación manual doble acción, tubería EMT red incendios, cámara CCTV, control de acceso,
  sensor magnético, reubicación puntos detección.

CAP10_ADICIONALES
  incluye: bodega, aseo de obra, equipos especiales, elementos que no se encuentran en los capítulos anteriores.
  Ejemplos: adecuación bodega, aseo y entrega de obra, equipo especial,señalización de obra, planos récord.

Reglas de inferencia:
1. Los dos ejemplos anteriores muestran el nivel de detalle y la variedad de actividades esperadas. Cada proyecto es diferente, usar los ejemplos como
referencia de detalle y no como lista fija de actividades.

2. Aplica tu conocimiento y criterio tecnico de interventor en obras constructivas para inferir actividades que se derivan del texto aunque no estén mencionadas explícitamente
3. Marca siempre las actividades inferidas con origen="inferida" y explica el supuesto en el campo observacion.

Reglas generales:
- Para Obra civil o en remodelacion se cumple que remodelación considera desmontes y demoliciones de lo que se va a reemplazar, segun lo que indica el texto
- Para Obra nueva en local comercial se cumple que puede incluir desconexiones de instalaciones anteriores del local
- Usa el tipo de proyecto, el estado de la obra y el contexto del texto para decidir qué actividades adicionales tienen sentido

No apliques reglas fijas y razona caso por caso como lo haria un interventor.

Supuestos:
1. Aplica estos valores cuando el texto no los especifique y agrega la alerta correspondiente en el campo alertas del proyecto.
2. Colocar altura_entrepiso: 2.40m pero se debe generar una alerta de supuesto: altura entrepiso 2.40m, confirmar"
3. Si no hay espacios definidos crear espacio "area_total" con area_total y una alerta de supuesto: proyecto sin espacios, se usó area total"

Preguntas:
Cuando la información no esté en el texto, agrega la pregunta en el campo alertas.

1. Preguntas bloqueantes: se generan cuando se tiene la informacion priomordial para la generacion de la planilla.
  - pregunta_bloqueante: cual es el area total del proyecto en m2?
  - pregunta_bloqueante: el proyecto es Obra Civil/Remodelacion u Obra nueva?
  - pregunta_bloqueante: cual es el tipo de proyecto?

2. Preguntas de alto impacto: se generan cuando son esenciales y pueden generar y una estimacion incorrecta si no se tiene esta informacion
  - pregunta: cuantos m2 tiene (nombre_espacio)?
  - pregunta: cual es la altura del entrepiso?
  - pregunta: cuantos banos tiene el proyecto?
  - pregunta: hay zona de cocina?

3. Detalle: se generan cuando la informacion es necesaria para mejorar la precision
  - pregunta: tiene referencia del material?
  - pregunta: tiene marca del material?

Reglas absolutas:
1. Responde solo con el JSON. Sin texto antes ni despues.
2. Todas las cantidades deben ser numeros mayores a cero, nunca usar null o None en cantidad, si no conoces la cantidad exacta, usa 1 para
   actividades globales (gl) o estima basandote en el area total del proyecto.
3. Nunca inventes referencias de materiales que no esten en el texto.
4. Si el texto menciona una marca o referencia, incluyela en el campo referencia. La descripcion debe contener la actividad tecnica.
5. Usa los valores exactos de los enums para capitulo, unidad, suministro y origen.
6. El nombre del espacio debe estar en minúsculas, sin tildes y con guion bajo
   en lugar de espacios. Ejemplo: "sala_principal", "bano_1", "area_general".
7. Si una actividad puede ir en varios capítulos, elige el más específico.
8. No repitas la misma actividad en el mismo espacio.
9. Desglosa actividades que son TIPOS distintos de trabajo. El campo
   cantidad representa cuántas unidades hay de ese tipo. NO crees una
   actividad por cada unidad individual del mismo tipo de elemento.
   Mal:  12 actividades "instalación tomacorriente normal"
         59 actividades "instalación lámpara spot riel"
   Bien: 1 actividad "instalación tomacorriente normal 15A" cantidad=12
         1 actividad "instalación lámpara tipo spot en riel 18W" cantidad=59

   si desglosa cuando son elementos físicamente diferentes entre si:
   mal:  "Mueble con lavamanos, mesón en sinterizado y grifería con sensor"
   bien: tres actividades separadas porque son elementos distintos:
         - "Mueble inferior en melamina"
         - "Lavamanos de sobreponer con instalación"
         - "Mesón en piedra sinterizada"
10. Usa kg solo para acero estructural u otros elementos que se midan por peso.
11. Las descripciones deben incluir la acción completa más el elemento y su
    especificación técnica. Usa el mismo nivel de detalle que un interventor
    de obra al escribir una planilla APU.
    mal:  "Estructura metálica para riel"
          "Piso porcelanato"
          "Cieloraso"
    bien: "Suministro e instalación de estructura metálica tipo channel ranurado"
          "Instalación enchape piso porcelanato gran formato 60x120"
          "Cieloraso en drywall con frescasa"
12. Jerarquía de actividades a generar:
    primero: extrae todo lo que dice explícitamente el texto con el máximo detalle posible.
    segundo: infiere las actividades que son consecuencia directa y necesaria de lo extraido (si hay piso nuevo entonces alistado previo, si hay muros nuevos
    en remodelación entonces desmonte previo; si hay cieloraso entonces tapas de inspección).
    no generes actividades genéricas del tipo de proyecto si el texto nolas sugiere. Aseo final, señalizacion, material de protección solo si
    el texto o el contexto del proyecto lo justifica claramente.
"""

max_intentos = 3

capitulos_apu = [c.value for c in capitulo]

api_key = st.secrets.get("OPENAI_api_key", "") if hasattr(st, "secrets") else os.getenv("OPENAI_api_key", "")

st.markdown(
    """
    <div style="display:flex;flex-direction:column;align-items:center;text-align:center;margin-top:24px;margin-bottom:8px">
      <div style="display:flex;align-items:center;gap:14px;justify-content:center">
        <div style="width:48px;height:48px;border-radius:50%;background:transparent;
                    border:3px solid white;flex-shrink:0;
                    display:flex;align-items:center;justify-content:center">
          <svg xmlns="http://www.w3.org/2000/svg" width="26" height="26" viewBox="0 0 24 24"
               fill="none" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M15 12l-8.5 8.5a2.12 2.12 0 0 1-3-3L12 9"/>
            <path d="M17.64 15L22 10.64"/>
            <path d="M20.91 11.7l-1.25-1.25c-.6-.6-.93-1.4-.93-2.25v-.86L16.01 4.6a5.56 5.56 0 0 0-3.94-1.64H9l.92.82A6.18 6.18 0 0 1 12 8.4v1.56l2 2h2.47l2.26 1.91"/>
          </svg>
        </div>
        <h1 style="margin:0;font-size:2.2rem;line-height:1.2">Generador de planillas APU</h1>
      </div>
      <p style="margin:10px 0 0 0;font-size:0.95rem;opacity:0.75">
        Describe tu proyecto y obtendrás los capítulos, actividades, unidad de medida y cantidades para tu estimación clase 2.
      </p>
    </div>
    """,
    unsafe_allow_html=True,
)

with st.sidebar:
    st.header("Configuración")
    modelo = "gpt-4o-mini"
    st.markdown(f"Modelo: {modelo}")
    temperatura = 0.0
    st.markdown("Temperatura: 0.0")

    def seccion_sidebar(titulo, items):
        lista = "".join(f"<li>{i}</li>" for i in items)
        st.markdown(
            f"""
            <div style="margin-top:24px">
              <span style="display:inline-block;border:1px solid rgba(128,128,128,0.4);
                           border-radius:8px;padding:2px 10px;
                           box-shadow:0 2px 4px rgba(0,0,0,0.15);
                           background:transparent"><strong>{titulo}</strong></span>
              <ul style="margin:8px 0 0 0;padding-left:18px">{lista}</ul>
            </div>
            """,
            unsafe_allow_html=True,
        )

    seccion_sidebar("Tipos de proyecto", [t.value.capitalize() for t in clasf_proyecto])
    st.divider()
    seccion_sidebar("Estado de obra", [e.value.capitalize() for e in estado_obra])
    st.divider()
    seccion_sidebar("Capítulos APU", capitulos_apu)

if "mensajes" not in st.session_state:
    st.session_state.mensajes = []     
if "resultado" not in st.session_state:
    st.session_state.resultado = None
if "contexto" not in st.session_state:
    st.session_state.contexto = ""   

def mostrar_resultado(resultado, col):
    with col:
        if resultado["schema_ok"] and resultado["proyecto"]:
            proy = proyecto.model_validate(resultado["proyecto"])
            nombre_proy = ""
            texto_input = resultado.get("texto", "")
            if texto_input:
                m = re.search(r'proyecto\s*:\s*([^\n,?\.]+)', texto_input, re.IGNORECASE)
                if m:
                    nombre_proy = m.group(1).strip()
            display_name = nombre_proy if nombre_proy else f"{proy.tipo.value.upper()} · {proy.estado.value.upper()}"
            st.markdown(
                f"<h3 style='margin-bottom:14px'>{display_name}</h3>",
                unsafe_allow_html=True,
            )

            card_style = "border:1px solid rgba(0,180,160,0.4);border-radius:8px;background:rgba(0,180,160,0.18);padding:18px 14px;text-align:center"
            c1, c2, c3, c4 = st.columns(4)
            for col_c, titulo, valor in [
                (c1, "Tipo",        proy.tipo.value.capitalize()),
                (c2, "Estado",      proy.estado.value.capitalize()),
                (c3, "Área",        f"{proy.area_total} m²" if proy.area_total else "—"),
                (c4, "Actividades", str(len(proy.actividades_planas))),
            ]:
                col_c.markdown(
                    f"<div style='{card_style}'>"
                    f"<div style='font-size:15px;opacity:0.75;margin-bottom:6px'>{titulo}</div>"
                    f"<div style='font-size:19px;font-weight:600'>{valor}</div></div>",
                    unsafe_allow_html=True,
                )

            st.divider()
            st.subheader("Planilla APU")
            df = pd.DataFrame(proy.actividades_planas)
            if not df.empty:
                df = df.rename(columns={
                    "espacio": "Espacio",
                    "capitulo": "Capítulo",
                    "descripcion": "Descripción",
                    "referencia": "Referencia",
                    "unidad": "Und",
                    "cantidad": "Cantidad",
                    "suministro": "Suministro",
                    "origen": "Origen",
                })

                def separar_capitulos(df_):
                    estilos = pd.DataFrame("", index=df_.index, columns=df_.columns)
                    cap_prev = None
                    for i in df_.index:
                        if df_.loc[i, "Capítulo"] != cap_prev and cap_prev is not None:
                            estilos.loc[i] = "border-top: 2px solid white"
                        cap_prev = df_.loc[i, "Capítulo"]
                    return estilos

                altura = 228
                st.dataframe(
                    df.style.apply(separar_capitulos, axis=None),
                    use_container_width=True,
                    hide_index=True,
                    height=altura,
                    column_config={
                        "Espacio": st.column_config.TextColumn("Espacio", width="small"),
                        "Capítulo": st.column_config.TextColumn("Capítulo", width="medium"),
                        "Descripción": st.column_config.TextColumn("Descripción", width="large"),
                        "Referencia": st.column_config.TextColumn("Referencia", width="small"),
                        "Und": st.column_config.TextColumn("Und", width="small"),
                        "Cantidad": st.column_config.NumberColumn("Cantidad", width="small", format="%.2f"),
                        "Suministro": st.column_config.TextColumn("Suministro", width="small"),
                        "Origen": st.column_config.TextColumn("Origen", width="small"),
                    },
                )
                csv = df.to_csv(index=False, encoding="utf-8-sig")
                st.download_button(
                    "Descargar CSV",
                    data=csv,
                    file_name="planilla_apu.csv",
                    mime="text/csv",
                )

            if not df.empty:
                st.divider()
                col_graf, col_tray = st.columns([1.2, 1], gap="large")

                with col_graf:
                    st.subheader("Resumen por capítulo")
                    espacios_unicos = sorted(df["Espacio"].unique())
                    orden = (
                        df.groupby("Capítulo")["Descripción"]
                          .count()
                          .sort_values(ascending=True)
                          .index.tolist()
                    )

                    fig = go.Figure()
                    for esp in espacios_unicos:
                        df_esp = df[df["Espacio"] == esp]
                        conteos = df_esp.groupby("Capítulo")["Descripción"].count().reindex(
                            orden, fill_value=0
                        )
                        fig.add_trace(go.Bar(
                            name=esp,
                            y=orden,
                            x=conteos.values,
                            orientation="h",
                            marker_color="rgba(160,160,160,0.45)",
                            marker_line=dict(color="rgba(200,200,200,0.7)", width=1),
                            text=conteos.values,
                            textposition="outside",
                            textfont=dict(size=11, color="white"),
                        ))

                    fig.update_layout(
                        barmode="group",
                        plot_bgcolor="rgba(0,0,0,0)",
                        paper_bgcolor="rgba(0,0,0,0)",
                        font_color="white",
                        xaxis=dict(
                            visible=False,
                        ),
                        yaxis=dict(
                            title="",
                            gridcolor="rgba(255,255,255,0.1)",
                            automargin=True,
                        ),
                        legend=dict(
                            title="Espacios",
                            bgcolor="rgba(0,0,0,0)",
                        ),
                        margin=dict(l=10, r=10, t=10, b=30),
                        height=300,
                    )
                    st.plotly_chart(fig, use_container_width=True)

                with col_tray:
                    st.subheader("Trayectoria del agente")
                    for paso in resultado["trajectory"]:
                        res_lower = str(paso['resultado']).lower()
                        color_res = "#e53935" if res_lower == "fallo" else "#43a047" if res_lower == "ok" else "inherit"
                        st.markdown(
                            f"[{paso['componente']}] {paso['decision']}: "
                            f"<span style='color:{color_res};font-weight:600'>`{paso['resultado']}`</span>",
                            unsafe_allow_html=True,
                        )
                    latencia = resultado.get("latencia_ms")
                    if latencia:
                        st.caption(f"Latencia: {latencia:.0f} ms")
        else:
            st.error("No se pudo generar la planilla.")
            if resultado.get("error_pydantic"):
                st.code(resultado["error_pydantic"])

st.markdown("""
<style>
.stMainBlockContainer, div[data-testid="stMainBlockContainer"] {
    padding-top: 2.5rem !important;
}
section[data-testid="stSidebar"] > div:first-child {
    padding-top: 2rem !important;
}
div[data-testid="stFormSubmitButton"] > button {
    background-color: rgba(0, 180, 160, 0.75) !important;
    border: 1px solid rgba(0, 180, 160, 0.9) !important;
    color: white !important;
    font-weight: 500 !important;
}
div[data-testid="stFormSubmitButton"] > button:hover {
    background-color: rgba(0, 180, 160, 1) !important;
    border-color: rgba(0, 180, 160, 1) !important;
}
</style>
""", unsafe_allow_html=True)

col_entrada, col_resultado = st.columns([1, 1.6], gap="large")

with col_entrada:
    st.markdown("<div style='margin-top:38px'></div>", unsafe_allow_html=True)
    chat_box = st.container(height=680, border=True)
    with chat_box:
        if not st.session_state.mensajes:
            st.caption("Tu proyecto")
        for msg in st.session_state.mensajes:
            alineacion = "right" if msg["role"] == "user" else "left"
            fondo = "rgba(0,180,160,0.15)" if msg["role"] == "user" else "rgba(255,255,255,0.07)"
            st.markdown(
                f"<div style='text-align:{alineacion};margin:6px 0'>"
                f"<span style='display:inline-block;background:{fondo};"
                f"border-radius:10px;padding:8px 14px;max-width:85%;text-align:left'>"
                f"{msg['content']}</span></div>",
                unsafe_allow_html=True,
            )

    with st.form("form_entrada", clear_on_submit=True):
        texto_input = st.text_area(
            "Descripción del proyecto",
            height=180,
            placeholder="Describe tu proyecto: ¿Cómo se llama tu proyecto? ¿Qué tipo de proyecto es? ¿En qué estado está la obra? ¿Algunas actividades, espacios o marcas de productos que vas a usar?...",
            label_visibility="collapsed",
        )
        _, col_nuevo, col_btn = st.columns([2, 1.2, 1])
        with col_nuevo:
            nuevo = st.form_submit_button("Nueva conversación", use_container_width=True)
        with col_btn:
            enviado = st.form_submit_button("Enviar", use_container_width=True)

    if nuevo:
        st.session_state.mensajes = []
        st.session_state.resultado = None
        st.session_state.contexto = ""
        st.rerun()

if enviado and texto_input.strip():
    if not api_key:
        with col_entrada:
            st.error("API Key no configurada. Contacta al administrador.")
        st.stop()

    st.session_state.mensajes.append({"role": "user", "content": texto_input.strip()})

    if st.session_state.contexto:
        st.session_state.contexto += f"\n\nRespuesta adicional: {texto_input.strip()}"
    else:
        st.session_state.contexto = texto_input.strip()

    with col_resultado:
        with st.spinner("Procesando..."):
            try:
                llm = ChatOpenAI(model=modelo, temperature=temperatura, api_key=api_key)
                resultado = run_agente(st.session_state.contexto, llm)
            except Exception as e:
                st.error(f"Error al ejecutar el agente: {e}")
                st.stop()

    st.session_state.resultado = resultado

    if resultado["schema_ok"] and resultado["proyecto"]:
        proy = proyecto.model_validate(resultado["proyecto"])
        partes = [proy.tipo.value, proy.estado.value]
        if proy.area_total:
            partes.append(f"{proy.area_total} m²")
        partes.append(f"{len(proy.actividades_planas)} actividades")
        respuesta = "Listo: " + " | ".join(partes)

        if proy.preguntas_pendientes:
            respuesta += "\n\nNecesito confirmar algunos datos:"
            for p in proy.preguntas_pendientes:
                respuesta += f"\n- {p.replace('pregunta:', '').strip()}"
        if proy.supuestos:
            respuesta += "\n\nSupuestos:"
            for s in proy.supuestos:
                respuesta += f"\n- {s.replace('supuesto:', '').strip()}"
        if proy.inconsistencias:
            respuesta += "\n\nAlertas:"
            for a in proy.inconsistencias:
                respuesta += f"\n- {a.replace('alerta:', '').strip()}"
    else:
        respuesta = "No se pudo generar la planilla, revisa la descripción."
        if resultado.get("error_pydantic"):
            respuesta += f" Error: {resultado['error_pydantic']}"

    st.session_state.mensajes.append({"role": "agent", "content": respuesta})
    st.rerun()

if st.session_state.resultado:
    mostrar_resultado(st.session_state.resultado, col_resultado)
