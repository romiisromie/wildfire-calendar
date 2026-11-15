"""Interface strings in English, Spanish and Russian. Keys are the English text; missing entries fall back to English."""
from __future__ import annotations

import re

LANGS = {"EN": "en", "ES": "es", "RU": "ru"}
lang = "en"

MONTHS = {
    "en": ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
    "es": ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"],
    "ru": ["янв", "фев", "мар", "апр", "май", "июн", "июл", "авг", "сен", "окт", "ноя", "дек"],
}

TR: dict[str, tuple[str, str]] = {  # english: (spanish, russian)
    # header & picker
    "When does this land burn, and is this year normal?": ("¿Cuándo arde esta tierra y es normal este año?",
                                                            "Когда горит эта земля и нормален ли этот год?"),
    "Country": ("País", "Страна"),
    "Choose area": ("Elegir área", "Выбор области"),
    "Example": ("Ejemplo", "Пример"),
    "Draw": ("Dibujar", "Нарисовать"),
    "Point": ("Punto", "Точка"),
    "Example: ready-made areas · Draw: rectangle or polygon on the map · Point: coordinates and a radius": (
        "Ejemplo: áreas listas · Dibujar: rectángulo o polígono en el mapa · Punto: coordenadas y radio",
        "Пример: готовые области · Нарисовать: прямоугольник или многоугольник на карте · Точка: координаты и радиус"),
    "Latitude": ("Latitud", "Широта"),
    "Longitude": ("Longitud", "Долгота"),
    "Radius, km": ("Radio, km", "Радиус, км"),
    "{km} km around {lat}°, {lon}°": ("{km} km alrededor de {lat}°, {lon}°", "{km} км вокруг {lat}°, {lon}°"),
    "Your drawn area": ("Tu área dibujada", "Нарисованная область"),
    "Clear drawing": ("Borrar dibujo", "Стереть"),
    "Use the ▭ or ⬠ tool on the map’s left edge to outline an area.": (
        "Usa la herramienta ▭ o ⬠ del borde izquierdo del mapa para marcar un área.",
        "Обведите область инструментом ▭ или ⬠ у левого края карты."),
    "Whole country": ("Todo el país", "Вся страна"),
    # sidebar
    "Settings": ("Ajustes", "Настройки"),
    "Activity measure": ("Medida de actividad", "Мера активности"),
    "Calendar colours": ("Colores del calendario", "Цвета календаря"),
    "Add a country": ("Añadir país", "Добавить страну"),
    "Country name as in NASA FIRMS": ("Nombre del país en NASA FIRMS", "Название страны как в NASA FIRMS"),
    "Download 2000–2025": ("Descargar 2000–2025", "Скачать 2000–2025"),
    "The online demo ships Kazakhstan and Argentina. To add any other country, run the app locally: python fetch.py Brazil --build": (
        "La demo en línea incluye Kazajistán y Argentina. Para añadir otro país, ejecuta la app localmente: python fetch.py Brazil --build",
        "Онлайн-демо содержит Казахстан и Аргентину. Чтобы добавить другую страну, запустите приложение локально: python fetch.py Brazil --build"),
    "Use letters only, e.g. United States.": ("Usa solo letras, p. ej. United States.",
                                              "Только латинские буквы, например United States."),
    "Active 0.1° cells": ("Celdas activas de 0,1°", "Активные ячейки 0,1°"),
    "Hotspot detections": ("Detecciones de focos", "Точки огня"),
    "Fire radiative power (MW)": ("Potencia radiativa (MW)", "Мощность огня (МВт)"),
    # map & readouts
    "Glow = VIIRS hotspots of the last three years · bright dots = fires of the last 7 days (NOAA-20) · dashed line = analysed area.": (
        "Brillo = focos VIIRS de los últimos tres años · puntos claros = fuegos de los últimos 7 días (NOAA-20) · línea discontinua = área analizada.",
        "Свечение = точки VIIRS за три года · яркие точки = пожары последних 7 дней (NOAA-20) · пунктир = анализируемая область."),
    "No area yet": ("Sin área", "Область не выбрана"),
    "Outline a place on the map": ("Marca un lugar en el mapa", "Обведите место на карте"),
    "Pick an example, draw a shape, or enter coordinates.": ("Elige un ejemplo, dibuja una forma o escribe coordenadas.",
                                                             "Выберите пример, нарисуйте область или введите координаты."),
    "No fire detections in this area. Try a larger one.": ("No hay detecciones en esta área. Prueba una más grande.",
                                                           "В этой области нет пожаров. Попробуйте область побольше."),
    "Area drawn. Switch **Choose area** to **Draw** to analyse it.": (
        "Área dibujada. Cambia **Elegir área** a **Dibujar** para analizarla.",
        "Область нарисована. Переключите **Выбор области** на **Нарисовать**."),
    "Land here burns mostly <em>{s}</em> ({p}% of a year’s fire)": (
        "Aquí la tierra arde sobre todo <em>{s}</em> ({p}% del fuego del año)",
        "Здесь горит в основном <em>{s}</em> ({p}% годового огня)"),
    ", with a second season <em>{s}</em>": (", con una segunda temporada <em>{s}</em>", ", второй сезон — <em>{s}</em>"),
    "{m} burned <em>{w} usual</em> ({r}× the median).": ("{m} ardió <em>{w} lo habitual</em> ({r}× la mediana).",
                                                          "{m}: огня <em>{w} обычного</em> ({r}× медианы)."),
    "far more than": ("mucho más que", "намного больше"),
    "more than": ("más que", "больше"),
    "less than": ("menos que", "меньше"),
    "about as much as": ("casi igual que", "примерно столько же, сколько"),
    "Since the 2000s, yearly fire is <em>{d} {p}%</em>.": ("Desde los años 2000, el fuego anual <em>{d} un {p}%</em>.",
                                                           "С 2000-х годовой объём огня <em>{d} на {p}%</em>."),
    "down": ("bajó", "снизился"),
    "up": ("subió", "вырос"),
    "Last 7 days · {a}–{b}": ("Últimos 7 días · {a}–{b}", "Последние 7 дней · {a}–{b}"),
    "{u} · normal for these days {m} · rank {r} of {n} · updated {t} UTC": (
        "{u} · normal para estos días {m} · puesto {r} de {n} · actualizado {t} UTC",
        "{u} · норма для этих дней {m} · место {r} из {n} · обновлено {t} UTC"),
    "Old vs new years comparable?": ("¿Se comparan años viejos y nuevos?", "Можно сравнивать старые и новые годы?"),
    "High": ("Alta", "Высокая"), "Medium": ("Media", "Средняя"), "Low": ("Baja", "Низкая"),
    "Insufficient": ("Insuficiente", "Мало данных"),
    "solid": ("sólida", "надёжно"), "careful": ("con cuidado", "осторожно"), "timing only": ("solo fechas", "только сроки"),
    "too little fire to test": ("muy poco fuego para probar", "слишком мало огня для проверки"),
    "{m} vs median": ("{m} vs mediana", "{m} против медианы"),
    "rank {r} of {n} years · usual {a}–{b}": ("puesto {r} de {n} años · habitual {a}–{b}",
                                               "место {r} из {n} лет · обычно {a}–{b}"),
    "{u} · this month usually has almost no fire here": ("{u} · este mes casi nunca hay fuego aquí",
                                                         "{u} · в этом месяце здесь обычно почти не горит"),
    "Too little fire in 2013–2025 to test the conversion here. Seasons are still valid.": (
        "Muy poco fuego en 2013–2025 para probar la conversión aquí. Las temporadas siguen siendo válidas.",
        "Слишком мало огня в 2013–2025, чтобы проверить пересчёт. Сезоны при этом надёжны."),
    "Old and new years are comparable (held-out error {e}%).": (
        "Los años viejos y nuevos son comparables (error fuera de muestra {e}%).",
        "Старые и новые годы можно сравнивать (ошибка на отложенных годах {e}%)."),
    "Seasons and big changes are reliable; small year-to-year differences are not ({e}%).": (
        "Las temporadas y los grandes cambios son fiables; las pequeñas diferencias entre años no ({e}%).",
        "Сезоны и крупные изменения надёжны, мелкие различия между годами — нет ({e}%)."),
    "Use for timing, not for amounts across 2012 ({e}% error).": (
        "Úsalo para fechas, no para cantidades antes y después de 2012 (error {e}%).",
        "Годится для сроков, но не для сравнения объёмов до и после 2012 (ошибка {e}%)."),
    "Worst year on record": ("Peor año registrado", "Худший год"),
    "{x}× a typical year": ("{x}× un año típico", "{x}× типичного года"),
    "Hotspots analysed": ("Focos analizados", "Проанализировано точек"),
    # tabs
    "Calendar": ("Calendario", "Календарь"), "This year": ("Este año", "Этот год"),
    "Climate & shift": ("Clima y cambios", "Климат и сдвиг"), "Seasons & events": ("Temporadas y eventos", "Сезоны и события"),
    "Harmonization": ("Armonización", "Гармонизация"), "Download": ("Descargar", "Скачать"), "Method": ("Método", "Метод"),
    "Months": ("Meses", "Месяцы"), "Weeks": ("Semanas", "Недели"),
    "not observed": ("sin observar", "нет наблюдений"),
    "VIIRS starts ↓": ("empieza VIIRS ↓", "начало VIIRS ↓"),
    "Brighter = more fire (log scale). Before 2012 values are MODIS converted to VIIRS units; empty cells were not fully observed.": (
        "Más claro = más fuego (escala log). Antes de 2012 los valores son MODIS convertidos a unidades VIIRS; las celdas vacías no se observaron completas.",
        "Ярче = больше огня (лог. шкала). До 2012 года — MODIS, пересчитанный в единицы VIIRS; пустые клетки наблюдались не полностью."),
    "usual range (10–90%)": ("rango habitual (10–90%)", "обычный разброс (10–90%)"),
    "median year": ("año mediano", "медианный год"),
    "{u} per week": ("{u} por semana", "{u} в неделю"),
    "{u} per month": ("{u} por mes", "{u} в месяц"),
    "above the usual range": ("sobre lo habitual", "выше обычного"), "within": ("dentro", "в норме"),
    "below": ("debajo", "ниже"),
    "“Usual” = complete years 2000–{y}.": ("«Habitual» = años completos 2000–{y}.", "«Обычно» = полные годы 2000–{y}."),
    # climate tab
    "No clear fire season here to analyse.": ("No hay una temporada de fuego clara.", "Чёткого пожарного сезона нет."),
    "NASA POWER weather is unavailable right now; showing season timing only.": (
        "El clima de NASA POWER no está disponible; solo se muestran fechas.",
        "Погода NASA POWER сейчас недоступна; показаны только сроки сезона."),
    "Season {s} · {p}% of yearly fire": ("Temporada {s} · {p}% del fuego anual", "Сезон {s} · {p}% годового огня"),
    "Too few complete seasons.": ("Muy pocas temporadas completas.", "Слишком мало полных сезонов."),
    "onset": ("inicio", "начало"), "middle": ("mitad", "середина"), "end": ("fin", "конец"),
    "Season starts": ("Inicio de temporada", "Начало сезона"), "Season ends": ("Fin de temporada", "Конец сезона"),
    "no clear shift": ("sin cambio claro", "сдвига нет"),
    "{d} days/decade, p = {p}": ("{d} días/década, p = {p}", "{d} дн./десятилетие, p = {p}"),
    "{d} days {w} / decade": ("{d} días {w} / década", "на {d} дн. {w} за 10 лет"),
    "earlier": ("antes", "раньше"), "later": ("después", "позже"),
    "MODIS alone {d} d/decade": ("solo MODIS {d} d/década", "только MODIS {d} дн./10 лет"),
    "✔ same on one sensor — not a 2012 artefact": ("✔ igual con un solo sensor — no es un artefacto de 2012",
                                                    "✔ то же на одном сенсоре — не артефакт 2012 года"),
    "⚠ not confirmed by MODIS alone": ("⚠ no confirmado solo con MODIS", "⚠ не подтверждается одним MODIS"),
    "After hot-dry-windy days": ("Tras días cálidos, secos y ventosos", "После жарких, сухих, ветреных дней"),
    "After calm-humid days": ("Tras días calmos y húmedos", "После тихих влажных дней"),
    "{x}× normal": ("{x}× lo normal", "{x}× нормы"),
    "90% range {a}–{b} over {n} seasons": ("rango 90% {a}–{b} en {n} temporadas", "90% диапазон {a}–{b}, {n} сезонов"),
    "Season timing: the day by which 10% (start), 50% and 90% (end) of a season’s fire had burned, each year. Trend = Theil–Sen slope, significance = Kendall test. Fire weather: daily hot-dry-windy index (vapour-pressure deficit × wind, NASA POWER) compared with its normal for the date; the next 3 days’ fire is compared with the same dates in other years. Coloured dot = the 90% range excludes 1 (no effect).": (
        "Fechas de temporada: día en que ardió el 10% (inicio), 50% y 90% (fin) del fuego de la temporada, cada año. Tendencia = pendiente de Theil–Sen, significancia = prueba de Kendall. Clima de fuego: índice cálido-seco-ventoso (déficit de presión de vapor × viento, NASA POWER) frente a su normal para la fecha; el fuego de los 3 días siguientes se compara con las mismas fechas de otros años. Punto de color = el rango 90% excluye 1 (sin efecto).",
        "Сроки сезона: день, к которому сгорело 10% (начало), 50% и 90% (конец) огня сезона, по годам. Тренд — наклон Тейла–Сена, значимость — тест Кендалла. Пожарная погода: индекс «жарко-сухо-ветрено» (дефицит упругости пара × ветер, NASA POWER) относительно нормы для даты; огонь следующих 3 дней сравнивается с теми же датами других лет. Цветная точка = 90% диапазон не включает 1 (нет эффекта)."),
    "Many seasons and dates are tested at once, so treat a single p < 0.05 as a lead to check, not as proof.": (
        "Se prueban muchas temporadas y fechas a la vez: un p < 0,05 aislado es una pista para verificar, no una prueba.",
        "Проверяется сразу много сезонов и дат, поэтому одиночное p < 0,05 — повод проверить, а не доказательство."),
    "Fire weather of the last 60 days": ("Clima de fuego de los últimos 60 días", "Пожарная погода за 60 дней"),
    "vs normal": ("vs normal", "к норме"),
    "hot-dry-windy": ("cálido-seco-ventoso", "жарко-сухо-ветрено"), "normal": ("normal", "норма"),
    "calm-humid": ("calmo-húmedo", "тихо-влажно"),
    "NASA POWER weather at the area centre, up to {d}.": ("Clima NASA POWER en el centro del área, hasta {d}.",
                                                          "Погода NASA POWER в центре области, до {d}."),
    # seasons & events
    "Fire seasons": ("Temporadas de fuego", "Пожарные сезоны"),
    "season": ("temporada", "сезон"), "peak week": ("semana pico", "пиковая неделя"),
    "share of yearly fire": ("parte del fuego anual", "доля годового огня"),
    "Documented fires — does the satellite record see them?": ("Incendios documentados: ¿los ve el registro satelital?",
                                                               "Известные пожары: видит ли их спутник?"),
    "reported fire": ("incendio reportado", "пожар из новостей"), "hotspots ±3 days": ("focos ±3 días", "точек ±3 дня"),
    "same dates, typical year": ("mismas fechas, año típico", "те же даты, обычный год"),
    "result": ("resultado", "результат"), "highest of 2013–2025": ("el mayor de 2013–2025", "максимум за 2013–2025"),
    "rank {r} of 13": ("puesto {r} de 13", "место {r} из 13"),
    "No documented fire inside this area.": ("No hay incendios documentados en esta área.",
                                             "В этой области нет задокументированных пожаров."),
    "Weeks far above normal for their time of year": ("Semanas muy por encima de lo normal para su época",
                                                      "Недели намного выше нормы для своего времени года"),
    "No strong anomalies.": ("Sin anomalías fuertes.", "Сильных аномалий нет."),
    # harmonization
    "How wrong is MODIS × factor on years it never saw?": ("¿Cuánto falla MODIS × factor en años que no vio?",
                                                           "Насколько ошибается MODIS × коэффициент на незнакомых годах?"),
    "raw MODIS": ("MODIS sin ajuste", "MODIS без пересчёта"), "one factor": ("un factor", "один коэффициент"),
    "monthly factor (used)": ("factor mensual (usado)", "по месяцам (используем)"),
    "held-out monthly error, %": ("error mensual fuera de muestra, %", "ошибка на отложенных годах, %"),
    "For each year 2013–2025 the factor is learned from the other years only, then that year’s monthly VIIRS totals are predicted from MODIS. Error = Σ|predicted − actual| / Σ actual.": (
        "Para cada año 2013–2025 el factor se aprende solo con los demás años y se predicen sus totales mensuales VIIRS desde MODIS. Error = Σ|predicho − real| / Σ real.",
        "Для каждого года 2013–2025 коэффициент обучается только на остальных годах, затем месячные суммы VIIRS этого года предсказываются по MODIS. Ошибка = Σ|прогноз − факт| / Σ факт."),
    "VIIRS sees this many times more than MODIS, by month": ("VIIRS ve tantas veces más que MODIS, por mes",
                                                             "Во сколько раз VIIRS видит больше MODIS, по месяцам"),
    "all-year ×{k}": ("todo el año ×{k}", "за весь год ×{k}"),
    "Overlap years: VIIRS vs converted MODIS": ("Años de solapamiento: VIIRS vs MODIS convertido",
                                                "Годы перекрытия: VIIRS и пересчитанный MODIS"),
    "MODIS raw": ("MODIS sin ajuste", "MODIS без пересчёта"), "MODIS × factor": ("MODIS × factor", "MODIS × коэффициент"),
    # download
    "Compare & download": ("Comparar y descargar", "Сравнить и скачать"),
    "Pick a period: how does it compare with every other year?": (
        "Elige un período: ¿cómo se compara con todos los demás años?",
        "Выберите период: как он выглядит на фоне всех остальных лет?"),
    "Period": ("Período", "Период"),
    "Selected period": ("Período elegido", "Выбранный период"),
    "Same dates, median year": ("Mismas fechas, año mediano", "Те же даты, медианный год"),
    "{x}× the median": ("{x}× la mediana", "{x}× медианы"),
    "Rank among {n} years": ("Puesto entre {n} años", "Место среди {n} лет"),
    "1 = most fire on these dates since 2000": ("1 = más fuego en estas fechas desde 2000",
                                                "1 = больше всего огня в эти даты с 2000 года"),
    "median": ("mediana", "медиана"),
    "Same calendar dates in every year of the record, on one harmonized scale: lighter bars before 2012 are MODIS converted to VIIRS units.": (
        "Mismas fechas en cada año del registro, en una sola escala armonizada: las barras claras antes de 2012 son MODIS convertido a unidades VIIRS.",
        "Те же календарные даты в каждом году, в единой шкале: светлые столбцы до 2012 года — MODIS, пересчитанный в единицы VIIRS."),
    "Choose a start and an end date, at most one year apart.": ("Elige una fecha de inicio y de fin, como máximo a un año.",
                                                               "Выберите начало и конец периода, не дальше года друг от друга."),
    "Hotspots in the period": ("Focos en el período", "Точки огня за период"),
    "every detection, both sensors": ("cada detección, ambos sensores", "каждая точка, оба сенсора"),
    "Period vs other years": ("Período vs otros años", "Период против других лет"),
    "one row per year": ("una fila por año", "строка на каждый год"),
    "Every chart has a camera button in its top-right corner to save it as a PNG.": (
        "Cada gráfico tiene un botón de cámara arriba a la derecha para guardarlo como PNG.",
        "У каждого графика справа вверху есть кнопка-камера: сохраняет его в PNG."),
    "Critical periods (fire seasons)": ("Períodos críticos (temporadas de fuego)", "Критические периоды (пожарные сезоны)"),
    "Critical period": ("Período crítico", "Критический период"),
    "Why harmonize: the trend from 2003–2010 to 2016–2025": ("Por qué armonizar: la tendencia de 2003–2010 a 2016–2025",
                                                             "Зачем гармонизация: тренд с 2003–2010 к 2016–2025"),
    "Sensors joined as they are": ("Sensores unidos sin ajuste", "Сенсоры склеены как есть"),
    "MODIS before 2012, VIIRS after": ("MODIS antes de 2012, VIIRS después", "MODIS до 2012, VIIRS после"),
    "wrong direction": ("dirección equivocada", "неверное направление"),
    "Harmonized record": ("Registro armonizado", "Гармонизированный ряд"),
    "MODIS × monthly factor, then VIIRS": ("MODIS × factor mensual, luego VIIRS", "MODIS × месячный коэффициент, затем VIIRS"),
    "Check: MODIS alone, all 25 years": ("Control: solo MODIS, los 25 años", "Проверка: только MODIS, все 25 лет"),
    "one sensor, no switch": ("un sensor, sin cambio", "один сенсор, без смены"),
    "Joining the two sensors as they are would show it <em>up {p}%</em> instead.": (
        "Unir los dos sensores sin ajuste mostraría, en cambio, <em>un aumento del {p}%</em>.",
        "Простая склейка двух сенсоров показала бы, наоборот, <em>рост на {p}%</em>."),
    "Download CSV": ("Descargar CSV", "Скачать CSV"),
    "Daily series": ("Serie diaria", "Ежедневный ряд"), "Hotspots": ("Focos", "Точки огня"),
    "year × month": ("año × mes", "год × месяц"), "every detection": ("cada detección", "каждая точка"),
    "{n} rows": ("{n} filas", "{n} строк"), "{n} days": ("{n} días", "{n} дней"),
}


def t(text: str, /, **kw) -> str:
    if lang != "en" and text in TR:
        text = TR[text][0 if lang == "es" else 1]
    return text.format(**kw) if kw else text


_MON_RE = re.compile(r"\b(" + "|".join(MONTHS["en"]) + r")\b")


def months(text: str) -> str:
    """Translate English month abbreviations inside a label like '09 Apr – 03 Jun'."""
    if lang == "en":
        return text
    return _MON_RE.sub(lambda m: MONTHS[lang][MONTHS["en"].index(m.group(1))], text)


def month_names() -> list[str]:
    return MONTHS[lang]
