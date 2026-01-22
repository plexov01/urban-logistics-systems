import time
import matplotlib

matplotlib.use('Agg')
import matplotlib.pyplot as plt
from src.core import CityMap
from src.engine import SimulationEngine

# --- НАСТРОЙКИ ТЕСТА ---
ITERATIONS_PER_PARAM = 5  # Можно менять на 1, 3, 10 и т.д.
MAX_STEPS_LIMIT = 2000
PENALTY_TIME = MAX_STEPS_LIMIT


def run_test_session(num_agents, traffic_prob):
    city_map = CityMap('data/citymap.txt')
    engine = SimulationEngine(city_map, num_agents, traffic_prob)
    engine.start()

    current_tick = 0
    try:
        while current_tick < MAX_STEPS_LIMIT:
            engine.step()
            current_tick += 1
            if engine.all_finished():
                break
    finally:
        engine.shutdown()

    paths, times, speeds = [], [], []
    raw_stats = list(engine.stats)

    for item in raw_stats:
        if isinstance(item, (tuple, list)):
            p_len, t_time = item
            paths.append(p_len)
            times.append(t_time)
            # Скорость: путь делить на время (тики)
            speeds.append(p_len / t_time if t_time > 0 else 0)
        else:
            paths.append(0)
            times.append(PENALTY_TIME)
            speeds.append(0)

    # Возвращаем средние по группе агентов
    count = len(paths) if paths else 1
    return sum(paths) / count, sum(times) / count, sum(speeds) / count


def run_benchmark(param_name, param_value, fixed_agents=None, fixed_prob=None):
    print(f"\n[ТЕСТ] {param_name} = {param_value} | Попыток: {ITERATIONS_PER_PARAM}")

    m_path, m_time, m_speed = 0, 0, 0

    for i in range(1, ITERATIONS_PER_PARAM + 1):
        agents = param_value if fixed_agents is None else fixed_agents
        prob = param_value if fixed_prob is None else fixed_prob

        p, t, v = run_test_session(agents, prob)
        print(f"  #{i}: Путь: {p:>4.1f} | Время: {t:>6.1f} | Скорость: {v:>5.3f}")

        m_path += p
        m_time += t
        m_speed += v

    return m_path / ITERATIONS_PER_PARAM, m_time / ITERATIONS_PER_PARAM, m_speed / ITERATIONS_PER_PARAM


def plot_results(x_data, paths, times, speeds, title, filename, xlabel):
    """Строит график с тремя показателями (использует 2 оси Y)"""
    fig, ax1 = plt.subplots(figsize=(12, 7))
    ax2 = ax1.twinx()

    # Путь и Время (Левая ось)
    ax1.plot(x_data, paths, 'g-o', label='Путь (клетки)', linewidth=2)
    ax1.plot(x_data, times, 'b-s', label='Время (тики)', linewidth=2)
    ax1.set_xlabel(xlabel)
    ax1.set_ylabel('Дистанция / Время', fontsize=12)
    ax1.legend(loc='upper left')
    ax1.grid(True, alpha=0.3)

    # Скорость (Правая ось)
    ax2.plot(x_data, speeds, 'r-^', label='Скорость (кл/тик)', linewidth=3)
    ax2.set_ylabel('Средняя скорость', color='r', fontsize=12)
    ax2.tick_params(axis='y', labelcolor='r')
    ax2.set_ylim(0, 1.1)  # Скорость не может быть больше 1
    ax2.legend(loc='upper right')

    plt.title(title)
    plt.tight_layout()
    plt.savefig(filename)
    plt.close()


def perform_analysis():
    # 1. ТРАФИК
    t_probs = [0.01, 0.05, 0.1, 0.2]
    res_p, res_t, res_v = [], [], []
    for p in t_probs:
        p_val, t_val, v_val = run_benchmark("Трафик", p, fixed_agents=2)
        res_p.append(p_val);
        res_t.append(t_val);
        res_v.append(v_val)

    plot_results(t_probs, res_p, res_t, res_v,
                 'Эффективность доставки vs Плотность трафика',
                 'analysis_traffic.png', 'Вероятность трафика')

    # 2. АГЕНТЫ
    a_counts = [2, 3, 4]
    res_p, res_t, res_v = [], [], []
    for c in a_counts:
        p_val, t_val, v_val = run_benchmark("Агенты", c, fixed_prob=0.05)
        res_p.append(p_val);
        res_t.append(t_val);
        res_v.append(v_val)

    # Для агентов используем строковые метки для графика
    plot_results([str(c) for c in a_counts], res_p, res_t, res_v,
                 'Эффективность доставки vs Количество агентов',
                 'analysis_agents.png', 'Количество агентов')


if __name__ == "__main__":
    perform_analysis()