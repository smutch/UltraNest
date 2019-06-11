import numpy as np
import shutil
import scipy.stats
import traceback
import json
import random
import sys
import os
import signal
import string


def main(args):
    ndim = args.x_dim
    paramnames = list(string.ascii_lowercase)[:ndim]
    
    np.random.seed(args.seed)
    if args.wrapped_dims:
        wrapped_params = [True] * ndim
    else:
        wrapped_params = None
    
    true_Z = None
    
    if args.log_dir is None:
        if args.delete_dir:
            return
        log_dir = None
    else:
        log_dir = args.log_dir + '-%s-%dd' % (args.problem, ndim)
    
        if args.delete_dir:
            shutil.rmtree(log_dir, ignore_errors=True)
    
    if args.problem == 'gauss':
        sigma = 0.01
        if args.wrapped_dims:
            centers = (np.sin(np.arange(ndim)/2.) + 1.) / 2.
        else:
            centers = (np.sin(np.arange(ndim)/2.) / 2. + 1.) / 2.
        true_Z = 0
        def loglike(theta):
            like = -0.5 * (((theta - centers)/sigma)**2).sum(axis=1) - 0.5 * np.log(2 * np.pi * sigma**2) * ndim
            return like

        def transform(x):
            return x
    elif args.problem == 'slantedeggbox':
        if not args.pass_transform:
            return
        
        def loglike(z):
            chi = (2. + (np.cos(z[:,:2] / 2.)).prod(axis=1))**5
            chi2 = -np.abs((z - 5 * np.pi) / 0.5).sum(axis=1)
            return chi + chi2

        def transform(x):
            return x * 100
    elif args.problem == 'funnel':
        if args.wrapped_dims: return
        if not args.pass_transform:
            return
        
        sigma = 0.01
        centers = np.sin(np.arange(ndim) / 2.)
        data = np.random.normal(centers, sigma).reshape((1, -1))

        def loglike(theta):
            sigma = 10**theta[:,0]
            like = -0.5 * (((theta[:,1:] - data)/sigma.reshape((-1, 1)))**2).sum(axis=1) - 0.5 * np.log(2 * np.pi * sigma**2) * ndim
            return like

        def transform(x):
            z = x * 20 - 10
            z[:,0] = x[:,0] * 6 - 3
            return z
        
        paramnames.insert(0, 'sigma')
    elif args.problem == 'loggamma':
        if args.wrapped_dims: return
        rv1a = scipy.stats.loggamma(1, loc=2./3, scale=1./30)
        rv1b = scipy.stats.loggamma(1, loc=1./3, scale=1./30)
        rv2a = scipy.stats.norm(2./3, 1./30)
        rv2b = scipy.stats.norm(1./3, 1./30)
        rv_rest = []
        for i in range(2, ndim):
            if i <= (ndim+2)/2:
                rv = scipy.stats.loggamma(1, loc=2./3., scale=1./30)
            else:
                rv = scipy.stats.norm(2./3, 1./30)
            rv_rest.append(rv)
            del rv

        def loglike(theta):
            L1 = np.log(0.5 * rv1a.pdf(theta[:,0]) + 0.5 * rv1b.pdf(theta[:,0]))
            L2 = np.log(0.5 * rv2a.pdf(theta[:,1]) + 0.5 * rv2b.pdf(theta[:,1]))
            Lrest = np.sum([rv.logpdf(t) for rv, t in zip(rv_rest, theta[:,2:].transpose())], axis=0)
            like = L1 + L2 + Lrest
            like = np.where(like < -300, -300 - ((np.asarray(theta) - 0.5)**2).sum(), like)
            assert like.shape == (len(theta),), (like.shape, theta.shape)
            return like
        def transform(x):
            return x
    
    from mininest import ReactiveNestedSampler
    sampler = ReactiveNestedSampler(paramnames, loglike, 
        transform=transform if args.pass_transform else None, 
        min_num_live_points=args.num_live_points,
        log_dir=log_dir, 
        append_run_num=not args.resume,
        wrapped_params=wrapped_params,
        cluster_num_live_points=args.cluster_num_live_points,
        max_num_live_points_for_efficiency=args.max_num_live_points_for_efficiency,
    )
    sampler.run(
        update_interval_iter_fraction=args.update_interval_iter_fraction,
        dlogz=args.dlogz,
        dKL=args.dKL,
        frac_remain=args.frac_remain,
        min_ess=args.min_ess,
        max_iters=args.max_iters,
        max_ncalls=int(args.max_ncalls),
    )
    sampler.print_results()
    results = sampler.results
    sampler.plot()
    if results['logzerr'] < 1.0 and true_Z is not None and args.num_live_points > 50:
        assert results['logz'] - results['logzerr'] * 2 < true_Z < results['logz'] + results['logzerr'] * 2
    return results

class AttrDict(dict):
    def __init__(self, *args, **kwargs):
        super(AttrDict, self).__init__(*args, **kwargs)
        self.__dict__ = self

if __name__ == '__main__':
    if len(sys.argv) > 1:
        for filename in sys.argv[1:]:
            print("loading configuration from file '%s'..." % filename)
            args = json.load(open(filename))
            print("Running with options:", args)
            main(AttrDict(args))
        sys.exit(0)
    
    Nrounds = int(os.environ.get('NROUNDS', '1'))
    for i in range(Nrounds):
        print("generating a random configuration...")
        def choose(args):
            # pick first (default) option most of the time
            if random.random() > 0.5:
                return args[0]
            else:
                return random.choice(args)
        
        args = dict(
            problem = choose(['gauss', 'slantedeggbox', 'funnel']),
            x_dim = choose([2, 1, 6, 10, 20]),
            seed = choose([1, 2, 3]),
            wrapped_dims = choose([False, True]),
            log_dir = choose(['logs/features', None]),
            delete_dir = choose([False, False, False, True]),
            pass_transform = choose([True, False]),
            num_live_points = choose([100, 50, 400, 1000]),
            resume = choose([False, True]),
            cluster_num_live_points = choose([50, 0]),
            max_num_live_points_for_efficiency = choose([400, 0]),
            update_interval_iter_fraction=choose([0.2, 1.0]),
            dlogz = choose([2.0, 0.5]),
            dKL = choose([1.0, 0.1]),
            frac_remain = choose([0.5, 0.001]),
            min_ess = choose([0, 4000]),
            max_iters = choose([None, 10000]),
            max_ncalls = choose([100000000., 10000., 100000.]),
        )
        id = hash(frozenset(args.items()))
        if os.path.exists('testfeatures/%s.done' % id):
            continue
        print("Running %s with options:" % id, args)
        
        def timeout_handler(signum, frame):
            raise Exception("Timeout")
        signal.signal(signal.SIGALRM, timeout_handler)
        
        signal.alarm(60 * (1 + args['x_dim'])) # give a few minutes
        try:
            main(AttrDict(args))
        except Exception as e:
            traceback.print_exc()
            filename = 'testfeatures/runsettings-%s-error.json' % id
            print("Storing configuration as '%s'. Options were:" % filename, args)
            with open(filename, 'w') as f:
                json.dump(args, f, indent=2)
            sys.exit(1)
        signal.alarm(0)
        with open('testfeatures/%s.done' % id, 'w'):
            pass
            
            
