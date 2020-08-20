import numpy as np

from creme.base import DriftDetector


class DDM(DriftDetector):
    r""" Drift Detection Method.

    Parameters
    ----------
    min_num_instances: int (default=30)
        The minimum required number of analyzed samples so change can be
        detected. This is used to avoid false detections during the early
        moments of the detector, when the weight of one sample is important.

    warning_level: float (default=2.0)
        Warning Level

    out_control_level: float (default=3.0)
        Out-control Level

    Notes
    -----
    DDM (Drift Detection Method) [1]_ is a concept change detection method
    based on the PAC learning model premise, that the learner's error rate
    will decrease as the number of analysed samples increase, as long as the
    data distribution is stationary.

    If the algorithm detects an increase in the error rate, that surpasses
    a calculated threshold, either change is detected or the algorithm will
    warn the user that change may occur in the near future, which is called
    the warning zone.

    The detection threshold is calculated in function of two statistics,
    obtained when `(pi + si)` is minimum:

    * :math:`p_{min}`: The minimum recorded error rate.
    * `s_{min}`: The minimum recorded standard deviation.

    At instant :math:`i`, the detection algorithm uses:

    * :math:`p_i`: The error rate at instant i.
    * :math:`s_i`: The standard deviation at instant i.

    The conditions for entering the warning zone and detecting change are
    as follows:

    * if :math:`p_i + s_i \geq p_{min} + 2 * s_{min}` -> Warning zone
    * if :math:`p_i + s_i \geq p_{min} + 3 * s_{min}` -> Change detected

    References
    ----------
    .. [1] João Gama, Pedro Medas, Gladys Castillo, Pedro Pereira Rodrigues: Learning
       with Drift Detection. SBIA 2004: 286-295

    Examples
    --------
    >>> import numpy as np
    >>> from creme.drift import DDM
    >>> np.random.seed(12345)

    >>> ddm = DDM()

    >>> # Simulate a data stream as a normal distribution of 1's and 0's
    >>> data_stream = np.random.randint(2, size=2000)
    >>> # Change the data distribution from index 999 to 1500, simulating an
    >>> # increase in error rate (1 indicates error)
    >>> data_stream[999:1500] = 1

    >>> # Update drift detector and verify if change is detected
    >>> for i, val in enumerate(data_stream):
    ...     in_drift, in_warning = ddm.add_element(val)
    ...     if in_drift:
    ...         print(f"Change detected at index {i}, input value: {val}")
    Change detected at index 1077, input value: 1

    """

    def __init__(self, min_num_instances=30, warning_level=2.0, out_control_level=3.0):
        super().__init__()
        self.sample_count = None
        self.miss_prob = None
        self.miss_std = None
        self.miss_prob_sd_min = None
        self.miss_prob_min = None
        self.miss_sd_min = None
        self.min_instances = min_num_instances
        self.warning_level = warning_level
        self.out_control_level = out_control_level
        self.estimation = None
        self.delay = None
        self.reset()

    def reset(self):
        """ reset

        Resets the change detector parameters.

        """
        super().reset()
        self.sample_count = 1
        self.miss_prob = 1.0
        self.miss_std = 0.0
        self.miss_prob_sd_min = float("inf")
        self.miss_prob_min = float("inf")
        self.miss_sd_min = float("inf")

    def add_element(self, prediction):
        """ Add a new element to the statistics

        Parameters
        ----------
        prediction: int (either 0 or 1)
            This parameter indicates whether the last sample analyzed was
            correctly classified or not. 1 indicates an error (miss-classification).

        Notes
        -----
        After calling this method, to verify if change was detected or if
        the learner is in the warning zone, one should call the super method
        detected_change, which returns True if concept drift was detected and
        False otherwise.

        """
        if self._in_concept_change:
            self.reset()

        self.miss_prob = self.miss_prob + (prediction - self.miss_prob) / float(self.sample_count)
        self.miss_std = np.sqrt(self.miss_prob * (1 - self.miss_prob) / float(self.sample_count))
        self.sample_count += 1

        self.estimation = self.miss_prob
        self._in_concept_change = False
        self._in_warning_zone = False
        self.delay = 0

        if self.sample_count < self.min_instances:
            return self._in_concept_change, self._in_warning_zone

        if self.miss_prob + self.miss_std <= self.miss_prob_sd_min:
            self.miss_prob_min = self.miss_prob
            self.miss_sd_min = self.miss_std
            self.miss_prob_sd_min = self.miss_prob + self.miss_std

        if self.miss_prob + self.miss_std > self.miss_prob_min + self.out_control_level \
                * self.miss_sd_min:
            self._in_concept_change = True

        elif self.miss_prob + self.miss_std > self.miss_prob_min + self.warning_level \
                * self.miss_sd_min:
            self._in_warning_zone = True

        else:
            self._in_warning_zone = False

        return self._in_concept_change, self._in_warning_zone
