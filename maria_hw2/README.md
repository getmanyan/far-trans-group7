# HW2 — LLM Paraphrase Encoder Subgroup Analysis (Maria, Group 7)

**Исследовательский вопрос:** Улучшает ли LLM-encoder (перефразирование описаний активов в стиле LLM-Rec) nDCG@10 по сравнению с original-text TF-IDF CBF у клиентов с короткой историей (1–3 актива) и у клиентов, чьи активы не имеют sector/industry, при одинаковых атрибутах as-of cutoff?

## Атрибуция и происхождение кода

- **Официальный код курса (RecSys-LLMs, commit** `f6850861ea20a51e1fb018ee4e5f840c2ac759e0`**):**
  - `starter.load_data` — загрузка данных, as-of фильтрация, ground truth.
  - `encoder.source_text`, `encoder.paraphrase_prompt`, `tfidf`, `combine_views`, `history_scores`, `predict`, `save_results` — алгоритмы paraphrase encoder.
- **Инфраструктура команды (Анастасия):**
  - `run_course_encoder.py` из корня репозитория — адаптация `Generator` для T4 (float16) и BF16 GPU. Вызывается через `run_maria_experiment.py` без изменений.
- **Собственный вклад (Мария):**
  - `run_maria_experiment.py` — тонкая обёртка, изолирующая запуск в папке Марии.
  - `analyze_maria.py` — строгий расчёт nDCG@10 по подгруппам, проверка data leakage, валидация manifest и per_user.
  - `test_maria.py` — unit-тесты логики подгрупп и обработки ошибок.
  - `hw2_maria_colab.ipynb` — воспроизводимый Colab-ноутбук.

## Файлы этой папки

| Файл | Назначение |
|---|---|
| `run_maria_experiment.py` | Обёртка над `run_course_encoder.py` Анастасии. Запускает paraphrase encoder в изолированной директории. |
| `analyze_maria.py` | Subgroup analysis (длина истории, полнота sector/industry) + data leakage check. |
| `test_maria.py` | Unit-тесты логики анализа. |
| `hw2_maria_colab.ipynb` | Полный Colab-пайплайн. |
| `README.md` | Этот файл. |

## Протокол

- **Модель:** `Qwen/Qwen3-1.7B`, revision `70d244cc86ccca08cf5af4e1e306ecf908b1ad5e`.
- **Course commit:** `f6850861ea20a51e1fb018ee4e5f840c2ac759e0`.
- **Выборка:** 100 детерминированных warm users (из `run_manifest.json`).
- **Cutoff:** 2021-06-01 (exclusive), окно оценки 30 дней.

## Подгруппы

1. **Длина истории (уникальные активы до cutoff):** 1, 2–3, 4+.
2. **Полнота метаданных (sector/industry):**
   - `meta_both`: все исторические активы имеют оба поля.
   - `meta_none`: все исторические активы не имеют обоих полей.
   - `meta_mixed`: смешанная или частичная полнота.

## Запуск тестов

```bash
cd maria_hw2
python -m unittest test_maria.py -v
```