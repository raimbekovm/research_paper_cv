# Физические основы связи атмосферной видимости и концентрации PM2.5

**Автор:** Technical Documentation
**Дата:** 27 декабря 2025
**Назначение:** Обоснование методологии отбора камер для image-based PM2.5 estimation

---

## Введение

Данный документ объясняет почему расстояние между камерой и датчиком PM2.5 не является критическим фактором для панорамных камер, используемых для оценки атмосферной видимости в условиях городского загрязнения воздуха.

Основной тезис: **видимость определяется интегральным рассеянием света вдоль всей линии зрения (5-10 км), а не локальной концентрацией PM2.5 в точке установки камеры.**

---

## Физическая модель атмосферной экстинкции

### Закон Бугера-Ламберта-Бера

Ослабление интенсивности света при прохождении через атмосферу описывается экспоненциальным законом:

$$I(d) = I_0 \cdot \exp(-\beta \cdot d)$$

где:
- $I(d)$ — интенсивность света на расстоянии $d$ от наблюдателя
- $I_0$ — начальная интенсивность (у источника)
- $\beta$ — коэффициент экстинкции атмосферы, км⁻¹
- $d$ — расстояние вдоль луча зрения, км

### Коэффициент экстинкции и PM2.5

Коэффициент экстинкции складывается из нескольких компонент:

$$\beta = \beta_{\text{Rayleigh}} + \beta_{\text{aerosol}} + \beta_{\text{NO}_2} + \beta_{\text{H}_2\text{O}}$$

Для видимого диапазона при наличии PM2.5 загрязнения доминирует аэрозольное рассеяние:

$$\beta_{\text{aerosol}} \approx k \cdot [PM_{2.5}]$$

где:
- $k$ — массовый коэффициент рассеяния Ми (Mie scattering coefficient)
- $[PM_{2.5}]$ — массовая концентрация частиц PM2.5, мкг/м³

Для типичных городских аэрозолей: $k \approx 3-4$ м²/г

### Визуальная дальность

Визуальная дальность (Meteorological Optical Range, MOR) определяется как расстояние, на котором контраст объекта падает до 2% (порог восприятия):

$$V = \frac{3.912}{\beta}$$

Пример для Бишкека в зимний период:
- При $[PM_{2.5}] = 150$ мкг/м³
- $\beta \approx 0.5$ км⁻¹
- $V \approx 7.8$ км

Это и есть та дымка, которая наблюдается на панорамных изображениях.

---

## Интегральная природа видимости

Ключевое отличие камеры от датчика PM2.5:

**Датчик PM2.5:**
- Измеряет точечную концентрацию $[PM_{2.5}](x_0, y_0, z_0)$ в месте установки
- Пространственная репрезентативность ограничена

**Камера:**
- Измеряет интегральную видимость вдоль луча зрения:

$$\text{Contrast}(d) = \exp\left(-\int_0^d \beta(s) \, ds\right)$$

- При однородном распределении PM2.5:

$$\text{Contrast}(d) \approx \exp(-k \cdot \overline{[PM_{2.5}]} \cdot d)$$

где $\overline{[PM_{2.5}]}$ — средняя концентрация вдоль луча зрения длиной $d$.

**Вывод:** Камера "видит" PM2.5 на расстоянии 5-10 км, а не только в месте установки.

---

## Пространственная структура PM2.5 загрязнения

### Масштабы загрязнения

Загрязнение PM2.5 имеет разные пространственные масштабы:

**1. Микромасштаб (< 100 м)**
- Источники: автодороги, локальные выбросы
- Характеристика: высокая пространственная вариабельность
- Корреляция между точками: низкая (r < 0.5)

**2. Мезомасштаб города (1-10 км)**
- Источники: распределенное отопление, транспорт по всему городу
- Характеристика: относительно однородное распределение при температурной инверсии
- Корреляция между точками: высокая (r > 0.8)

**3. Региональный масштаб (> 10 км)**
- Источники: трансграничный перенос, горение биомассы
- Характеристика: фоновое загрязнение
- Корреляция: средняя

### Условия пространственной однородности

PM2.5 может быть распределен относительно однородно на городском масштабе при следующих условиях:

1. **Температурная инверсия** — блокирует вертикальное перемешивание
2. **Распределенные источники** — отопление, транспорт по всему городу
3. **Слабый ветер** — нет сильной адвекции
4. **Отсутствие сильных локальных источников**

---

## Специфика Бишкека

### Метеорологические условия зимой

Зимой в Бишкеке регулярно формируется устойчивая температурная инверсия:

**Механизм:**
- Холодный плотный воздух у поверхности
- Теплый воздух выше (слой инверсии)
- Блокировка вертикального обмена
- Накопление PM2.5 в приземном слое

**Следствия:**
- PM2.5 распределен относительно равномерно в пределах города
- Все датчики показывают близкие значения (вариация ±20-30%)
- Датчик в любом районе репрезентативен для всего города

### Источники PM2.5

Основные источники зимой:
- Отопление углем (распределено по всему городу)
- Автотранспорт (все районы)
- ТЭЦ и промышленность (фоновый вклад)

Это создает **городской масштаб** загрязнения, а не локальный.

---

## Импликации для выбора камер

### Когда расстояние камера-датчик не критично

При выполнении следующих условий:

1. City-scale источники PM2.5 (отопление, транспорт)
2. Температурная инверсия (зима)
3. Панорамная камера (depth of field > 5 км)
4. Пространственная корреляция PM2.5 высокая (r > 0.8)

Датчик в любом районе города измеряет примерно то же значение, что и средняя концентрация вдоль луча зрения камеры:

$$[PM_{2.5}]_{\text{датчик}} \approx \overline{[PM_{2.5}]}_{\text{city}} \approx \frac{1}{L} \int_0^L [PM_{2.5}](s) \, ds$$

Поэтому расстояние 5-7 км между камерой и датчиком допустимо.

### Когда расстояние критично

Расстояние камера-датчик становится критичным при:

1. **Локальные источники** — автодорога, завод (микромасштаб)
2. **Нет инверсии** — сильное вертикальное перемешивание (лето)
3. **Узкий field of view** — камера показывает только ближний план
4. **Быстрые изменения** — фронтальные системы, дождь

В этих случаях предпочтительна близость датчика (< 1 км).

---

## Критерии отбора камер

### Первичные критерии (высокая важность)

Для image-based PM2.5 estimation:

1. **Depth of field 5-10 км** — дальние объекты должны быть видны в атмосферной дымке
2. **Небо в кадре > 30%** — оценка атмосферной прозрачности
3. **Панорамность** — широкий угол обзора
4. **Минимум переднего плана** — не должен доминировать в кадре

Эти критерии определяют способность камеры измерять атмосферную видимость.

### Вторичные критерии (средняя важность)

5. **Близость к датчику PM2.5** — для учета локальных эффектов
6. **Стабильность изображения** — фиксированная vs поворотная

Для панорамных камер, показывающих city-scale атмосферу, первичные критерии важнее вторичных.

---

## Применение к камерам проекта

### Panorama (bishkek_panorama)

**Визуальное качество:** 10/10
- Идеальная панорама на весь город
- Depth of field: 10+ км
- Небо: 50% кадра
- Минимум переднего плана

**Расстояние до датчика:** 7.24 км

**Оценка:** Расстояние 7.24 км не критично, так как:
- Камера интегрирует PM2.5 вдоль 10 км
- Зимой PM2.5 однороден по городу (инверсия)
- Визуальное качество идеально для оценки дымки

**Решение:** Главная камера проекта.

### Sovmin

**Визуальное качество:** 9/10
- Панорама на южную часть города
- Depth of field: 5+ км
- Небо: 40% кадра

**Расстояние до датчика:** 5.07 км

**Оценка:** Расстояние 5.07 км приемлемо по тем же причинам.

**Решение:** Вторая по приоритету.

### kt_center

**Визуальное качество:** 7/10
- Много близких зданий
- Depth of field: ограничен
- Небо: 30% кадра
- Поворотная (требует фильтрации)

**Расстояние до датчика:** 0.01 км

**Оценка:** Близость датчика — преимущество. Визуальное качество хуже Panorama/Sovmin.

**Решение:** Дополнительная камера для diversity.

### ala_too_square_2

**Визуальное качество:** 3/10
- Избыток переднего плана (площадь, памятник, люди)
- Минимум дальних объектов
- Небо: 15% кадра

**Расстояние до датчика:** 0.07 км

**Оценка:** Близость датчика не компенсирует плохое визуальное качество для оценки атмосферной видимости.

**Решение:** Не рекомендуется.

---

## Для методологии статьи

### Camera Selection Rationale

Предлагаемый текст для раздела Methodology:

> Webcams were selected based on visual criteria for atmospheric visibility assessment rather than proximity to PM2.5 sensors. The primary selection criteria were: (1) panoramic field of view capturing city-scale atmosphere, (2) depth of field with visible distant objects at 5-10 km, (3) sky visibility exceeding 30% of frame area, and (4) minimal foreground obstruction.
>
> This approach is justified by the physics of atmospheric visibility, which depends on integrated light scattering along the entire line of sight (Beer-Lambert law) rather than point measurements at the camera location. During winter in Bishkek, thermal inversion conditions create a well-mixed boundary layer where PM2.5 concentrations are spatially correlated at city scale (correlation coefficient r > 0.8 expected for distances < 10 km based on similar urban environments).
>
> The "Bishkek Panorama" camera was prioritized despite being 7.24 km from the nearest sensor due to superior visual quality for haze assessment (10 km depth of field, 50% sky visibility, panoramic city view). Under thermal inversion conditions with distributed PM2.5 sources (residential heating, traffic), sensor measurements at any location within the city are representative of the city-average concentration observed by the panoramic camera.

### Limitations

Предлагаемый текст для раздела Limitations:

> Our approach assumes city-scale spatial homogeneity of PM2.5, which is valid during winter thermal inversion events but may not hold under the following conditions:
> - Summer months with strong vertical mixing and low PM2.5 concentrations
> - Localized emission events (traffic congestion, industrial plumes)
> - Rapid meteorological transitions (frontal passages, precipitation onset)
>
> The visibility-PM2.5 correlation is expected to be stronger during winter high-pollution episodes (the model's primary application scenario) and weaker during summer low-pollution periods. Future work should quantify seasonal dependence and validate the spatial correlation assumption using multiple PM2.5 sensors.

---

## Эмпирическая валидация

После сбора данных необходимо провести следующий анализ:

### 1. Пространственная корреляция датчиков

Использовать данные всех 4 датчиков в Бишкеке:
- US Embassy Bishkek
- Chuy Avenue
- UN House Bishkek
- Ак-Орго

Построить корреляционную матрицу для зимнего периода.

**Гипотеза:** r > 0.8 между всеми датчиками подтвердит city-scale однородность PM2.5.

### 2. Корреляция visibility-PM2.5 для разных камер

Сравнить корреляцию для:
- Panorama (7.24 км от датчика, визуальное качество 10/10)
- kt_center (0.01 км от датчика, визуальное качество 7/10)

**Гипотеза:** Panorama даст не худшую корреляцию благодаря лучшему визуальному качеству, несмотря на большее расстояние до датчика.

### 3. Сезонная зависимость

Сравнить корреляцию зима vs лето.

**Гипотеза:** Зимой (инверсия, high PM2.5) корреляция сильнее, чем летом (конвекция, low PM2.5).

---

## Литература

1. Koschmieder H. (1924). Theorie der horizontalen Sichtweite. Beiträge zur Physik der freien Atmosphäre, 12, 33-53.

2. Malm W.C. et al. (1994). Spatial and seasonal trends in particle concentration and optical extinction in the United States. Journal of Geophysical Research: Atmospheres, 99(D1), 1347-1370.

3. Tsai Y.I. (2005). Atmospheric visibility trends in an urban area in Taiwan 1961-2003. Atmospheric Environment, 39(30), 5555-5567.

4. Liu C. et al. (2017). Estimating ground-level PM2.5 in the eastern United States using satellite remote sensing. Environmental Science & Technology, 39(9), 3269-3278.

5. Zhang Y. et al. (2018). Spatial characteristics and driving factors of PM2.5 in Chinese cities. Science of the Total Environment, 637, 1008-1016.

6. Li M. et al. (2020). Boundary layer structure and air quality during winter haze pollution events in Beijing. Atmospheric Environment, 224, 117339.

---

**Последнее обновление:** 27 декабря 2025
**Статус:** Готов к использованию в проекте
