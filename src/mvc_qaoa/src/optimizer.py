"""Classical optimization wrapper for QAOA parameters.

Implements two optimizers:
    - COBYLA (scipy): derivative-free, deterministic trust-region.
    - SPSA (built-in): stochastic gradient approximation, ideal for noisy
      quantum evaluations where each measurement is a random sample.
"""

import time
from typing import List, Dict, Callable
import numpy as np
from scipy.optimize import minimize


def optimize_qaoa(
    objective_fn: Callable[[np.ndarray], float],
    p: int,
    method: str = "SPSA",
    maxiter: int = 80,
    shots_per_eval: int = 4096,
    random_restarts: int = 5
) -> Dict:
    """Run classical optimizer for QAOA angles.

    Supports multiple random restarts and keeps the best result.

    Args:
        objective_fn: Function(params) -> expected_cost.
        p: Number of QAOA layers.
        method: Optimizer method ("SPSA", "COBYLA", "Nelder-Mead").
        maxiter: Max iterations per restart.
        shots_per_eval: Shots used in each quantum evaluation.
        random_restarts: Number of random initial guesses to try.

    Returns:
        Dict with best_params, best_cost, history, time_seconds, etc.
    """
    best_result = None
    best_cost = float("inf")

    for restart in range(random_restarts):
        history: List[float] = []
        trajectory: List[List[float]] = []

        # Wider random initialisation: gamma in [0, pi], beta in [0, pi/2]
        x0 = np.concatenate([
            np.random.uniform(0.0, np.pi, size=p),      # gamma
            np.random.uniform(0.0, np.pi / 2, size=p)   # beta
        ])

        t0 = time.time()

        if method.upper() == "SPSA":
            # SPSA hyperparameters (Spall 1998 standard values)
            a, c_param = 0.05, 0.1
            alpha_decay, gamma_decay = 0.602, 0.101
            A = maxiter / 10.0

            theta = np.array(x0, dtype=float)
            best_local_cost = float("inf")
            best_local_params = theta.copy()

            for k in range(maxiter):
                a_k = a / (A + k + 1) ** alpha_decay
                c_k = c_param / (k + 1) ** gamma_decay

                # Symmetric Bernoulli perturbation
                delta = np.random.choice([-1, 1], size=theta.shape)

                # Two evaluations (this is the whole point of SPSA)
                f_plus = objective_fn(theta + c_k * delta)
                f_minus = objective_fn(theta - c_k * delta)

                # Gradient estimate
                g_hat = (f_plus - f_minus) / (2.0 * c_k) * delta

                # Update
                theta = theta - a_k * g_hat

                # Evaluate at new point for history/trajectory
                f_new = objective_fn(theta)
                history.append(float(f_new))
                trajectory.append(theta.tolist())

                if f_new < best_local_cost:
                    best_local_cost = f_new
                    best_local_params = theta.copy()

            result = {
                "x": best_local_params,
                "fun": best_local_cost,
                "nfev": 2 * maxiter,
                "success": True,
                "message": "SPSA completed maxiter iterations.",
            }
        else:
            def cb(xk):
                val = objective_fn(xk)
                history.append(float(val))
                trajectory.append(xk.tolist())

            result = minimize(
                objective_fn,
                x0,
                method=method,
                options={"maxiter": maxiter},
                callback=cb,
            )

        elapsed = time.time() - t0
        final_cost = float(result["fun"])

        if final_cost < best_cost:
            best_cost = final_cost
            best_result = {
                "best_params": result["x"].tolist(),
                "best_cost": final_cost,
                "history": history,
                "trajectory": trajectory,
                "iterations": len(history),
                "time_seconds": elapsed,
                "restart": restart,
                "success": result["success"],
                "message": result["message"],
            }

    # Split params into gamma and beta
    params = np.array(best_result["best_params"])
    best_result["gammas"] = params[:p].tolist()
    best_result["betas"] = params[p:].tolist()

    return best_result
