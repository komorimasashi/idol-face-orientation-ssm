data {
  int<lower=1> T;
  int<lower=1> G;

  array[T] int<lower=1, upper=G> grp_id;

  vector[T] y;
  vector<lower=0>[T] y_se;
  array[T] int<lower=0, upper=1> is_obs;

  vector<lower=0>[T] delta_t;
  array[T] int<lower=1, upper=T> prev_idx;
  array[T] int<lower=0, upper=1> is_start;
}

parameters {
  vector[T] level_state;

  vector[G] eff_level;
  vector<lower=0>[G] rw_level;
}

model {
  eff_level ~ normal(0, 5);
  rw_level ~ normal(0, 1);

  for (t in 1:T) {
    int g = grp_id[t];

    if (is_start[t] == 1) {
      level_state[t] ~ normal(eff_level[g], 5);
    } else {
      int p = prev_idx[t];
      real dt = delta_t[t];
      level_state[t] ~ normal(level_state[p], rw_level[g] * sqrt(dt));
    }

    if (is_obs[t] == 1) {
      y[t] ~ normal(level_state[t], y_se[t]);
    }
  }
}

generated quantities {
  vector[G] mean_level;
  vector[T] y_rep;

  for (t in 1:T) {
    y_rep[t] = normal_rng(level_state[t], y_se[t]);
  }

  for (g in 1:G) {
    real s = 0;
    int n = 0;
    for (t in 1:T) {
      if (grp_id[t] == g) {
        s += level_state[t];
        n += 1;
      }
    }
    mean_level[g] = s / n;
  }
}
