from methods import diffusion_emd
from functools import partial
from sklearn.metrics import pairwise_distances
import numpy as np
from methods import evaluate
from methods import pairwise_mmd
from methods import pairwise_emd
from methods import pairwise_mean_diff
from methods import pairwise_sinkhorn
from methods import phemd
from methods import tree_emd
from methods import mean_approx
from methods import graph_mmd_exact, graph_mmd
from sklearn.preprocessing import StandardScaler
from tqdm import tqdm

from MultiscaleEMD import dataset
import itertools
import pandas as pd


def run_ablation(
    seeds=5,
    dataset_name="swiss_roll",
    n_neighbors=10,
    n_clusters=4,
    n_levels=4,
    n_trees=1,
    clustering_methods="kmeans",
):
    methods = {
        "Exact": pairwise_emd,
        "TreeEMD": tree_emd,
    }
    if isinstance(n_neighbors, int):
        n_neighbors = [n_neighbors]
    if isinstance(n_clusters, int):
        n_clusters = [n_clusters]
    if isinstance(n_levels, int):
        n_levels = [n_levels]
    if isinstance(n_trees, int):
        n_trees = [n_trees]
    if isinstance(clustering_methods, str):
        clustering_methods = [clustering_methods]
    ks = [1, 5, 10, 25, 50]
    # dataset_name = "s_curve"
    n_distributions_list = [100]  # , 50, 100]
    n_points_per_distribution = 20
    version = "0.0.3"

    iterator = itertools.product(
        range(seeds),
        n_distributions_list,
        n_neighbors,
        n_clusters,
        n_levels,
        n_trees,
        clustering_methods,
    )
    results2 = []
    exact_results = {}
    for args in tqdm(list(iterator)):
        seed, n_distributions, neighbors, clusters, levels, trees, cmethod = args
        if dataset_name == "tree":
            ds = dataset.Tree(n_distributions=n_distributions)
        else:
            ds = dataset.SklearnDataset(
                name=dataset_name,
                n_distributions=n_distributions,
                n_points_per_distribution=n_points_per_distribution,
                random_state=42 + seed,
            )
        labels = ds.labels
        labels /= labels.sum(0)
        X = ds.X
        X_std = StandardScaler().fit_transform(X)
        results = tree_emd(
            X_std,
            labels,
            n_neighbors=neighbors,
            n_clusters=clusters,
            n_levels=levels,
            n_trees=trees,
            cluster_method=cmethod,
        )
        if n_distributions not in exact_results:
            exact_results[n_distributions] = pairwise_emd(
                X_std, labels, n_neighbors=neighbors
            )

        results2.append(
            (
                "TreeEMD",
                *args,
                *evals,
                *results[-2:],
            )
        )
    df = pd.DataFrame(
        results2,
        columns=[
            "Method",
            "Seed",
            "# distributions",
            "# Neighbors",
            "# Clusters",
            "# levels",
            "# trees",
            "Clustering Method",
            "SpearmanR",
            *[f"P@{k}" for k in ks],
            "10-NN time (s)",
            "All-pairs time(s)",
        ],
    )
    df.to_pickle(
        f"results_{dataset_name}_{n_points_per_distribution}_{seeds}_{n_clusters}_{n_levels}_{n_trees}_{clustering_methods}_{version}.pkl"
    )
    return df


def run_sklearn_test(dataset_name, seeds=5):
    methods = {
        "DiffusionEMD": diffusion_emd,
        # "PhEMD": phemd,
        "Exact": pairwise_emd,
        "Sinkhorn": pairwise_sinkhorn,
        # "Mean": pairwise_mean_diff,
        # "TreeEMD": tree_emd,
        # "Graph MMD (Exact)": graph_mmd_exact,
        "Graph MMD (Chebyshev)": graph_mmd,
    }
    methods = {
        #"Graph MMD (Exact)": graph_mmd_exact,
        # "rbf-kernel-MMD": pairwise_mmd,
        "Graph MMD (Chebyshev, 8)": partial(graph_mmd, order=8),
        "Graph MMD (Chebyshev, 16)": partial(graph_mmd, order=16),
        "Graph MMD (Chebyshev, 32)": partial(graph_mmd, order=32),
        "Graph MMD (Chebyshev, 64)": partial(graph_mmd, order=64),
        "Graph MMD (Chebyshev, 128)": partial(graph_mmd, order=128),
    }
    n_neighbors = 10
    ks = [1, 5, 10, 25]
    n_distributions_list = [100]  # , 50, 100]
    n_points_per_distribution = 100
    version = "1.0.7"
    results2 = []
    for seed in range(seeds):
        for n_distributions in n_distributions_list:
            if dataset_name == "tree":
                ds = dataset.Tree(n_distributions=n_distributions)
            elif dataset_name == "swiss_roll":
                ds = dataset.SwissRoll(
                    n_distributions=n_distributions,
                    n_points_per_distribution=n_points_per_distribution,
                    random_state=42 + seed,
                )
                true_coords = np.stack([ds.means[:, 1], ds.t / 10], axis=1)
                exact_distances = pairwise_distances(true_coords, metric="euclidean")
            else:
                ds = dataset.SklearnDataset(
                    name=dataset_name,
                    n_distributions=n_distributions,
                    n_points_per_distribution=n_points_per_distribution,
                    random_state=42 + seed,
                )
                true_coords = np.stack([ds.means[:, 1], ds.t * 3], axis=1)
                exact_distances = pairwise_distances(true_coords, metric="euclidean")
            labels = ds.labels
            labels /= labels.sum(0)
            X = ds.X
            X_std = X
            # X_std = StandardScaler().fit_transform(X)

            results = {}
            for name, fn in methods.items():
                results.update({name: fn(X_std, labels, n_neighbors=n_neighbors)})
                print(f"{name} with M={n_distributions} took {results[name][-1]:0.2f}s")

            for name, res in results.items():
                results2.append(
                    (
                        name,
                        seed,
                        n_distributions,
                        *evaluate(res[1], exact_distances, ks=ks),
                        # *evaluate(res[1], results["Exact"][1], ks=ks),
                        *res[-2:],
                    )
                )
    df = pd.DataFrame(
        results2,
        columns=[
            "Method",
            "Seed",
            "# distributions",
            "SpearmanR",
            *[f"P@{k}" for k in ks],
            "10-NN time (s)",
            "All-pairs time(s)",
        ],
    )
    df.to_pickle(
        f"results_{dataset_name}_{n_points_per_distribution}_{seeds}_{version}.pkl"
    )
    return df


def run_sklearn_test_fast(dataset_name, seeds=5):
    methods = {
        "DiffusionEMD": diffusion_emd,
        # "PhEMD": phemd,
        # "Mean": mean_approx,
        # "TreeEMD": tree_emd,
    }
    n_neighbors = 10
    ks = [1, 5, 10, 25]
    n_distributions_list = [20000]  # , 50, 100]
    # n_distributions_list = [500, 750, 1000, 2000, 5000, 10000, 20000, 30000, 50000]  # , 50, 100]
    n_points_per_distribution = 100
    version = "0.1.5"
    results2 = []
    for seed in range(seeds):
        for n_distributions in n_distributions_list:
            if dataset_name == "tree":
                ds = dataset.Tree(n_distributions=n_distributions)
            else:
                ds = dataset.SklearnDataset(
                    name=dataset_name,
                    n_distributions=n_distributions,
                    n_points_per_distribution=n_points_per_distribution,
                    random_state=42 + seed,
                )
            labels = ds.labels
            labels /= labels.sum(0)
            X = ds.X
            X_std = StandardScaler().fit_transform(X)

            results = {}
            for name, fn in methods.items():
                if name == "PhEMD" and n_distributions > 5000:
                    continue
                    # Skip things that take > 10min
                if name == "DiffusionEMD" and n_distributions > 20000:
                    continue
                results.update({name: fn(X_std, labels, n_neighbors=n_neighbors)})
                print(f"{name} with M={n_distributions} took {results[name][-1]:0.2f}s")

            for name, res in results.items():
                if name == "DiffusionEMD" and n_distributions > 5000:
                    evals = [np.nan] * (len(ks) + 1)
                else:
                    evals = evaluate(res[1], results["TreeEMD"][1], ks=ks)
                results2.append(
                    (
                        name,
                        seed,
                        n_distributions,
                        *evals,
                        *res[-2:],
                    )
                )
    df = pd.DataFrame(
        results2,
        columns=[
            "Method",
            "Seed",
            "# distributions",
            "SpearmanR",
            *[f"P@{k}" for k in ks],
            "10-NN time (s)",
            "All-pairs time(s)",
        ],
    )
    df.to_pickle(
        f"results_{dataset_name}_{n_points_per_distribution}_{seeds}_{version}.pkl"
    )
    return df


if __name__ == "__main__":
    # run_sklearn_test_fast(dataset_name="tree", seeds=3)
    run_sklearn_test(dataset_name="swiss_roll", seeds=10)
    exit()

    run_ablation(
        seeds=10,
        dataset_name="tree",
        # dataset_name="swiss_roll",
        n_neighbors=10,
        n_clusters=[2, 3, 4, 5, 6, 7, 8],
        n_levels=[2, 3, 4, 5, 6, 7, 8],
        n_trees=[1, 4, 8, 16, 32, 64],
        clustering_methods=["kmeans"],  # , "random-kd"],
    )
