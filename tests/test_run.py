import numpy as np
import shutil
import pytest

def test_run():
    from mininest import NestedSampler

    def loglike(z):
        a = np.array([-0.5 * sum([((xi - 0.83456 + i*0.1)/0.5)**2 for i, xi in enumerate(x)]) for x in z])
        b = np.array([-0.5 * sum([((xi - 0.43456 - i*0.1)/0.5)**2 for i, xi in enumerate(x)]) for x in z])
        return np.logaddexp(a, b)

    def transform(x):
        return 10. * x - 5.
    
    paramnames = ['Hinz', 'Kunz']

    sampler = NestedSampler(paramnames, loglike, transform=transform, num_live_points=400)
    r = sampler.run(log_interval=50)
    open('nestedsampling_results.txt', 'a').write("%.3f\n" % r['logz'])
    sampler.plot()

def test_reactive_run():
    from mininest import ReactiveNestedSampler

    def loglike(z):
        a = np.array([-0.5 * sum([((xi - 0.83456 + i*0.1)/0.5)**2 for i, xi in enumerate(x)]) for x in z])
        b = np.array([-0.5 * sum([((xi - 0.43456 - i*0.1)/0.5)**2 for i, xi in enumerate(x)]) for x in z])
        return np.logaddexp(a, b)

    def transform(x):
        return 10. * x - 5.
    
    paramnames = ['Hinz', 'Kunz']

    sampler = ReactiveNestedSampler(paramnames, loglike, transform=transform, min_num_live_points=400)
    r = sampler.run(log_interval=50)
    open('nestedsampling_reactive_results.txt', 'a').write("%.3f\n" % r['logz'])
    sampler.plot()

@pytest.mark.parametrize("dlogz", [0.5, 0.1, 0.01])
def test_run_resume(dlogz):
    from mininest import NestedSampler
    sigma = 0.01
    ndim = 1

    def loglike(theta):
        like = -0.5 * (((theta - 0.5)/sigma)**2).sum(axis=1) - 0.5 * np.log(2 * np.pi * sigma**2) * ndim
        return like

    def transform(x):
        return x
    
    paramnames = ['a']
    def myadd(row):
        assert False, (row, 'should not need to add more points in resume')

    last_results = None
    #for dlogz in 0.5, 0.1, 0.01:
    np.random.seed(int(dlogz*100))
    shutil.rmtree('logs/test-run-gauss1d', ignore_errors=True)
    for i in range(2):
        sampler = NestedSampler(paramnames, loglike, transform=transform, 
            num_live_points=400, log_dir='logs/test-run-gauss1d', 
            append_run_num=False)
        r = sampler.run(log_interval=50, dlogz=dlogz)
        sampler.print_results()
        sampler.pointstore.close()
        if i == 1:
            sampler.pointstore.add = myadd
        del r['weighted_samples']
        del r['samples']
        if last_results is not None:
            print("ran with dlogz:", dlogz)
            print("first run gave:", last_results)
            print("second run gave:", r)
            assert last_results['logzerr'] < 1.0
            assert r['logzerr'] < 1.0
            assert np.isclose(last_results['logz'], r['logz'], atol=0.5)
        last_results = r


@pytest.mark.parametrize("dlogz,min_ess", [(0.5, 0), (0.2, 0), (0.5, 100), (0.5, 500)])
def test_reactive_run_resume(dlogz, min_ess):
    from mininest import ReactiveNestedSampler
    sigma = 0.01
    ndim = 1

    def loglike(theta):
        like = -0.5 * (((theta - 0.5)/sigma)**2).sum(axis=1) - 0.5 * np.log(2 * np.pi * sigma**2) * ndim
        return like

    paramnames = ['a']
    
    def myadd(row):
        assert False, (row, 'should not need to add more points in resume')
    
    last_results = None
    shutil.rmtree('logs/test-run-gauss1d', ignore_errors=True)
    for i in range(2):
        np.random.seed(int(dlogz*100 + min_ess))
        sampler = ReactiveNestedSampler(paramnames, loglike, 
            min_num_live_points=100, 
            log_dir='logs/test-run-gauss1d', 
            cluster_num_live_points=0,
            append_run_num=False)
        if i == 1:
            sampler.pointstore.add = myadd
        r = sampler.run(log_interval=1000, 
            max_num_improvement_loops=0,
            dlogz=dlogz, min_ess=min_ess, dKL=1e100)
        sampler.print_results()
        sampler.pointstore.close()
        del r['weighted_samples']
        del r['samples']
        if last_results is not None:
            print("ran with dlogz:", dlogz)
            print("first run gave:", last_results)
            print("second run gave:", r)
            assert last_results['logzerr'] < 1.0
            assert r['logzerr'] < 1.0
            assert np.isclose(last_results['logz'], r['logz'], atol=0.5)
        last_results = r


if __name__ == '__main__':
    #test_run_resume()
    test_reactive_run_resume()
    #test_reactive_run()
    #test_run()
