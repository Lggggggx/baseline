"""
Meta features designing for binary classification tasks 
 in the pool based active learning scenario.
"""
import os
import numpy as np 
from sklearn.cluster import KMeans
from sklearn.metrics import confusion_matrix
from sklearn.preprocessing import Normalizer,minmax_scale
from sklearn.utils.validation import check_array
from sklearn.datasets import make_classification
from sklearn.svm import SVC

from model import naive_bayes_classifier, knn_classifier, logistic_regression_classifier, \
    random_forest_classifier, decision_tree_classifier, svm_classifier, svm_cross_validation, gradient_boosting_classifier

classifiers = {'NB':naive_bayes_classifier,   
                'KNN':knn_classifier,  
                'LR':logistic_regression_classifier,  
                'RF':random_forest_classifier,  
                'DT':decision_tree_classifier,  
                'SVM':svm_classifier,  
            'SVMCV':svm_cross_validation,  
                'GBDT':gradient_boosting_classifier  
}

def randperm(n, k=None):
    """Generate a random array which contains k elements range from (n[0]:n[1])

    Parameters
    ----------
    n: int or tuple
        range from [n[0]:n[1]], include n[0] and n[1].
        if an int is given, then n[0] = 0

    k: int, optional (default=end - start + 1)
        how many numbers will be generated. should not larger than n[1]-n[0]+1,
        default=n[1] - n[0] + 1.

    Returns
    -------
    perm: list
        the generated array.
    """
    if isinstance(n, np.generic):
        n = np.asscalar(n)
    if isinstance(n, tuple):
        if n[0] is not None:
            start = n[0]
        else:
            start = 0
        end = n[1]
    elif isinstance(n, int):
        start = 0
        end = n
    else:
        raise TypeError("n must be tuple or int.")

    if k is None:
        k = end - start + 1
    if not isinstance(k, int):
        raise TypeError("k must be an int.")
    if k > end - start + 1:
        raise ValueError("k should not larger than n[1]-n[0]+1")

    randarr = np.arange(start, end + 1)
    np.random.shuffle(randarr)
    return randarr[0:k]

class DataSet():
    """

    Parameters
    ----------
    X: 2D array, optional (default=None) [n_samples, n_features]
        Feature matrix of the whole dataset. It is a reference which will not use additional memory.

    y: array-like, optional (default=None) [n_samples]
        Label matrix of the whole dataset. It is a reference which will not use additional memory.
        
    """
    def __init__(self, X, y, dataset_name):
        if not isinstance(X, (list, np.ndarray)):
            raise ValueError("")
        self.X = X
        self.y = y
        self.dataset_name = dataset_name
        self.n_samples, self.n_features =  np.shape(X)
        self.distance = None
    
    def get_cluster_center(self, n_clusters=10, method='Euclidean'):
        """Use the Kmeans in sklearn to get the cluster centers.

        Parameters
        ----------
        n_clusters: int 
            The number of cluster centers.
        Returns
        -------
        data_cluster_centers: np.ndarray
            The samples in origin dataset X is the closest to the cluster_centers.
        index_cluster_centers: np.ndarray
            The index corresponding to the samples in origin data set.     
        """
        if self.distance is None:
            self.get_distance()
        data_cluster = KMeans(n_clusters=n_clusters, random_state=0).fit(self.X)
        data_origin_cluster_centers = data_cluster.cluster_centers_
        closest_distance_data_cluster_centers = np.zeros(n_clusters) + np.infty
        index_cluster_centers = np.zeros(n_clusters, dtype=int) - 1

        # obtain the cluster centers index
        for i in range(self.n_samples):
            for j in range(n_clusters):
                if method == 'Euclidean':
                    distance = np.linalg.norm(X[i] - data_origin_cluster_centers[j])
                    if distance < closest_distance_data_cluster_centers[j]:
                        closest_distance_data_cluster_centers[j] = distance
                        index_cluster_centers[j] = i

        if(np.any(index_cluster_centers == -1)):
            raise IndexError("data_cluster_centers_index is wrong")

        return X[index_cluster_centers], index_cluster_centers

    def get_distance(self, method='Euclidean'):
        """

        Parameters
        ----------
        method: str
            The method calculate the distance.
        Returns
        -------
        distance_martix: 2D
            D[i][j] reprensts the distance between X[i] and X[j].
        """
        if self.n_samples == 1:
            raise ValueError("There is only one sample.")
        
        distance = np.zeros((self.n_samples, self.n_samples))
        for i in range(1, self.n_samples):
            for j in range(i+1, self.n_samples):
                if method == 'Euclidean':
                    distance[i][j] = np.linalg.norm(self.X[i] - self.X[j])
        
        self.distance = distance + distance.T
        return self.distance
    
    def split_data(self, test_ratio=0.3, initial_label_rate=0.05, split_count=10, saving_path='.'):
        """Split given data.

        Parameters
        ----------
        test_ratio: float, optional (default=0.3)
            Ratio of test set

        initial_label_rate: float, optional (default=0.05)
            Ratio of initial label set
            e.g. Initial_labelset*(1-test_ratio)*n_samples

        split_count: int, optional (default=10)
            Random split data _split_count times

        saving_path: str, optional (default='.')
            Giving None to disable saving.

        Returns
        -------
        train_idx: list
            index of training set, shape like [n_split_count, n_training_indexes]

        test_idx: list
            index of testing set, shape like [n_split_count, n_testing_indexes]

        label_idx: list
            index of labeling set, shape like [n_split_count, n_labeling_indexes]

        unlabel_idx: list
            index of unlabeling set, shape like [n_split_count, n_unlabeling_indexes]
        """
        # check parameters
        len_of_parameters = [len(self.X) if X is not None else None, len(self.y) if y is not None else None]
        number_of_instance = np.unique([i for i in len_of_parameters if i is not None])
        if len(number_of_instance) > 1:
            raise ValueError("Different length of instances and _labels found.")
        else:
            number_of_instance = number_of_instance[0]

        instance_indexes = np.arange(number_of_instance)

        # split
        train_idx = []
        test_idx = []
        label_idx = []
        unlabel_idx = []
        for i in range(split_count):
            rp = randperm(number_of_instance - 1)
            cutpoint = round((1 - test_ratio) * len(rp))
            tp_train = instance_indexes[rp[0:cutpoint]]
            train_idx.append(tp_train)
            test_idx.append(instance_indexes[rp[cutpoint:]])
            cutpoint = round(initial_label_rate * len(tp_train))
            if cutpoint <= 1:
                cutpoint = 1
            label_idx.append(tp_train[0:cutpoint])
            unlabel_idx.append(tp_train[cutpoint:])

        self.split_save(train_idx=train_idx, test_idx=test_idx, label_idx=label_idx,
                unlabel_idx=unlabel_idx, path=saving_path)
        return train_idx, test_idx, label_idx, unlabel_idx

    def split_load(self, path):
        """Load split from path.

        Parameters
        ----------
        path: str
            Path to a dir which contains train_idx.txt, test_idx.txt, label_idx.txt, unlabel_idx.txt.

        Returns
        -------
        train_idx: list
            index of training set, shape like [n_split_count, n_training_samples]

        test_idx: list
            index of testing set, shape like [n_split_count, n_testing_samples]

        label_idx: list
            index of labeling set, shape like [n_split_count, n_labeling_samples]

        unlabel_idx: list
            index of unlabeling set, shape like [n_split_count, n_unlabeling_samples]
        """
        if not isinstance(path, str):
            raise TypeError("A string is expected, but received: %s" % str(type(path)))
        saving_path = os.path.abspath(path)
        if not os.path.isdir(saving_path):
            raise Exception("A path to a directory is expected.")

        ret_arr = []
        for fname in ['train_idx.txt', 'test_idx.txt', 'label_idx.txt', 'unlabel_idx.txt']:
            if not os.path.exists(os.path.join(saving_path, fname)):
                if os.path.exists(os.path.join(saving_path, fname.split()[0] + '.npy')):
                    ret_arr.append(np.load(os.path.join(saving_path, fname.split()[0] + '.npy')))
                else:
                    ret_arr.append(None)
            else:
                ret_arr.append(np.loadtxt(os.path.join(saving_path, fname)))
        return ret_arr[0], ret_arr[1], ret_arr[2], ret_arr[3]

    def split_save(self, train_idx, test_idx, label_idx, unlabel_idx, path):
        """Save the split to file for auditting or loading for other methods.

        Parameters
        ----------
        saving_path: str
            path to save the settings. If a dir is not provided, it will generate a folder called
            'alipy_split' for saving.

        """
        if path is None:
            return
        else:
            if not isinstance(path, str):
                raise TypeError("A string is expected, but received: %s" % str(type(path)))

        saving_path = os.path.abspath(path)
        if os.path.isdir(saving_path):
            np.savetxt(os.path.join(saving_path, self.dataset_name + '_train_idx.txt'), train_idx)
            np.savetxt(os.path.join(saving_path, self.dataset_name + '_test_idx.txt'), test_idx)
            if len(np.shape(label_idx)) == 2:
                np.savetxt(os.path.join(saving_path, self.dataset_name + '_label_idx.txt'), label_idx)
                np.savetxt(os.path.join(saving_path, self.dataset_name + '_unlabel_idx.txt'), unlabel_idx)
            else:
                np.save(os.path.join(saving_path, self.dataset_name + '_label_idx.npy'), label_idx)
                np.save(os.path.join(saving_path, self.dataset_name + '_unlabel_idx.npy'), unlabel_idx)
        else:
            raise Exception("A path to a directory is expected.")


def mate_data(X, y, distance, cluster_center_index, label_indexs, unlabel_indexs, modelPredictions, query_index):
    """Calculate the meta data according to the current model,dataset and five rounds before information.


    Parameters
    ----------
    X: 2D array
        Feature matrix of the whole dataset. It is a reference which will not use additional memory.

    y:  {list, np.ndarray}
        The true label of the each round of iteration,corresponding to label_indexs.
    
    distance: 2D
        distance[i][j] reprensts the distance between X[i] and X[j].

    cluster_center_index: np.ndarray
        The index corresponding to the samples which is the result of cluster in origin data set.  

    label_indexs: {list, np.ndarray} shape=(number_iteration, corresponding_label_index)
        The label indexs of each round of iteration,

    unlabel_indexs: {list, np.ndarray} shape=(number_iteration, corresponding_unlabel_index)
        The unlabel indexs of each round of iteration,

    modelPredictions: {list, np.ndarray} shape=(number_iteration, corresponding_perdiction)


    query_index: {list, np.ndarray}
        The unlabel samples will be queride,and calculate the performance improvement after add to the labelset.

    Returns
    -------
    metadata: 2D array
        The meta data about the current model and dataset.
    """

    for i in range(6):
        assert(np.shape(X)[0] == np.shape(modelPredictions[i])[0]) 
        if(not isinstance(label_indexs[i], np.ndarray)):
            label_indexs[i] = np.array(label_indexs[i])
        if(not isinstance(unlabel_indexs[i], np.ndarray)):
            unlabel_indexs[i] = np.array(unlabel_indexs[i])
    
    n_samples, n_feature = np.shape(X)
    query_index_size = len(query_index)
    n_feature_data = n_feature * np.ones((query_index_size, 1))
    current_label_size = len(label_indexs[5])
    current_label_y = y[label_indexs[5]]
    current_unlabel_size = len(unlabel_indexs[5])
    current_prediction = modelPredictions[5]

    ratio_label_positive = (sum(current_label_y > 0)) / current_label_size
    ratio_label_positive_data = ratio_label_positive * np.ones_like(n_feature_data)
    ratio_label_negative = (sum(current_label_y < 0)) / current_label_size
    ratio_label_negative_data = ratio_label_negative * np.ones_like(n_feature_data)

    ratio_unlabel_positive = (sum(current_prediction[unlabel_indexs[5]] > 0)) / current_unlabel_size
    ratio_unlabel_positive_data = ratio_unlabel_positive * np.ones_like(n_feature_data)
    ratio_unlabel_negative = (sum(current_prediction[unlabel_indexs[5]] < 0)) / current_unlabel_size
    ratio_unlabel_negative_data = ratio_unlabel_negative * np.ones_like(n_feature_data)


    # the same dataset the same cluster centers
    # data_cluster = KMeans(n_clusters=10, random_state=0).fit(X)
    # data_origin_cluster_centers_10 = data_cluster.cluster_centers_
    # closest_distance_data_cluster_centers_10 = np.zeros(10) + np.infty
    # data_cluster_centers_10_index = np.zeros(10, dtype=int) - 1

    # # obtain the cluster centers index
    # for i in range(n_samples):
    #     for j in range(10):
    #         distance = np.linalg.norm(X[i] - data_origin_cluster_centers_10[j])
    #         if distance < closest_distance_data_cluster_centers_10[j]:
    #             closest_distance_data_cluster_centers_10[j] = distance
    #             data_cluster_centers_10_index[j] = i

    data_cluster_centers_10 = X[cluster_center_index]
    if(np.any(data_cluster_centers_10_index == -1)):
        raise IndexError("data_cluster_centers_10_index is wrong")
    
    sorted_labelperdiction_index = np.argsort(current_prediction[label_indexs[5]])
    sorted_current_label_data = X[label_indexs[5][sorted_labelperdiction_index]]
    
    label_10_equal = [sorted_current_label_data[int(i * current_label_size)] for i in np.arange(0, 1, 0.1)]
    label_10_equal_index = [label_indexs[5][sorted_labelperdiction_index][int(i * current_label_size)] for i in np.arange(0, 1, 0.1)]

    sorted_unlabelperdiction_index = np.argsort(current_prediction[unlabel_indexs[5]])
    sorted_current_unlabel_data = X[unlabel_indexs[5][sorted_unlabelperdiction_index]]
    unlabel_10_equal = [sorted_current_unlabel_data[int(i * current_unlabel_size)] for i in np.arange(0, 1, 0.1)]
    unlabel_10_equal_index = [unlabel_indexs[5][sorted_unlabelperdiction_index][int(i * current_unlabel_size)] for i in np.arange(0, 1, 0.1)]

              
    distance_query_data = None
    cc_sort_index = []

    for i in query_index:
        i_cc = []
        i_l10e = []
        i_u10e = []
        for j in range(10):
            # cal the ith in query_index about 
            # i_cc.append(np.linalg.norm(X[i] - data_cluster_centers_10[j]))
            # i_l10e.append(np.linalg.norm(X[i] - label_10_equal[j]))
            # i_u10e.append(np.linalg.norm(X[i] - unlabel_10_equal[j]))
            i_cc.append(distance[i][cluster_center_index[j]])
            i_l10e.append(distance[i][label_10_equal_index[j]])
            i_u10e.append(distance[i][unlabel_10_equal_index[j]])

        i_cc = minmax_scale(i_cc)
        i_cc_sort_index = np.argsort(i_cc)
        cc_sort_index.append(i_cc_sort_index)
        i_l10e = minmax_scale(i_l10e)
        i_u10e = minmax_scale(i_u10e)
        i_distance = np.hstack((i_cc[i_cc_sort_index], i_l10e, i_u10e))
        if distance_query_data is None:
            distance_query_data = i_distance
        else:
            distance_query_data = np.vstack((distance_query_data, i_distance))

    ratio_tn = []
    ratio_fp = []
    ratio_fn = []
    ratio_tp = []
    label_pre_10_equal = []
    labelmean = []
    labelstd = []
    unlabel_pre_10_equal = []
    round5_ratio_unlabel_positive = []
    round5_ratio_unlabel_negative = []
    unlabelmean = []
    unlabelstd = []   
    for i in range(6):
        label_size = len(label_indexs[i])
        unlabel_size = len(unlabel_indexs[i])
        cur_prediction = modelPredictions[i]
        label_ind = label_indexs[i]
        unlabel_ind = unlabel_indexs[i]

        tn, fp, fn, tp = confusion_matrix(y[label_ind], cur_prediction[label_ind], labels=[-1, 1]).ravel()
        ratio_tn.append(tn / label_size)
        ratio_fp.append(fp / label_size)
        ratio_fn.append(fn / label_size)
        ratio_tp.append(tp / label_size)

        sort_label_pred = np.sort(minmax_scale(cur_prediction[label_ind]))
        i_label_10_equal = [sort_label_pred[int(i * label_size)] for i in np.arange(0, 1, 0.1)]
        label_pre_10_equal = np.r_[label_pre_10_equal, i_label_10_equal]
        labelmean.append(np.mean(i_label_10_equal))
        labelstd.append(np.std(i_label_10_equal))

        round5_ratio_unlabel_positive.append((sum(current_prediction[unlabel_ind] > 0)) / unlabel_size)
        round5_ratio_unlabel_negative.append((sum(current_prediction[unlabel_ind] < 0)) / unlabel_size)
        sort_unlabel_pred = np.sort(minmax_scale(cur_prediction[unlabel_ind]))
        i_unlabel_10_equal = [sort_unlabel_pred[int(i * unlabel_size)] for i in np.arange(0, 1, 0.1)]
        unlabel_pre_10_equal = np.r_[unlabel_pre_10_equal, i_unlabel_10_equal]
        unlabelmean.append(np.mean(i_unlabel_10_equal))
        unlabelstd.append(np.std(i_unlabel_10_equal))
    model_infor = np.hstack((ratio_tp, ratio_fp, ratio_tn, ratio_fn, label_pre_10_equal, labelmean, labelstd, \
         round5_ratio_unlabel_positive, round5_ratio_unlabel_negative, unlabel_pre_10_equal, unlabelmean, unlabelstd))
    model_infor_data = model_infor * np.ones_like(n_feature_data)

    fx_data = None
    k = 0
    for i in query_index:
        f_x_a = []
        # f_x_b = []
        f_x_c = []
        f_x_d = []
        # print('data_cluster_centers_10_index[cc_sort_index[k]]', data_cluster_centers_10_index[cc_sort_index[k]])
        for round in range(6):
            predict = minmax_scale(modelPredictions[round])
            for j in range(10):
                f_x_a.append(predict[i] - predict[data_cluster_centers_10_index[cc_sort_index[k][j]]])
            for j in range(10):
                f_x_c.append(predict[i] - predict[label_10_equal_index[j]])
            for j in range(10):
                f_x_d.append(predict[i] - predict[unlabel_10_equal_index[j]])
        fdata = np.hstack((current_prediction[i], f_x_a, f_x_c, f_x_d))
        if fx_data is None:
            fx_data = fdata
        else:
            fx_data = np.vstack((fx_data, fdata))
        k += 1

    metadata = np.hstack((n_feature_data, ratio_label_positive_data, ratio_label_negative_data, \
         ratio_unlabel_positive_data, ratio_unlabel_negative_data, distance_query_data, model_infor_data, fx_data))
    print('The shape of meta_data: ', np.shape(metadata))
    return metadata


if __name__ == "__main__":
    X, y = make_classification(n_samples=100, n_features=5, n_classes=2)
    y[y==0] = -1
    d = DataSet(X, y, 'test')
    cd, cdi = d.get_cluster_center()

    train, test, l_ind, u_ind = d.split_data(split_count=6)

    print(np.shape(train))
    print(np.shape(l_ind))

    print(np.shape(u_ind))
    print(l_ind[5])
    
    models = []
    decision_value = []
    prediction = []

    for i in range(6):
        model = SVC()
        model.fit(X[l_ind[i]], y[l_ind[i]])
        prediction.append(model.predict(X))
        decision_value.append(model.decision_function(X))
        models.append(model)
    
    query_index = [i for i in range(15, 21)]
    query_index = np.array(query_index)
    meta = mate_data(X, y, l_ind, u_ind, prediction, query_index)
