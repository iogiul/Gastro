# TODO: use Montecarlo to estimate the errors
def vxvyvz(ra, dec, l, b, mura, mudec, vrad, dist, parallax=False, vlsr=220, vsun=(-11.1, 12.24, 7.25), zsun=0, rsun=8,
		   emura=None, emudec=None, evrad=None, edist=None, MCerror=False):
	"""
	Pass from observed quantities to Galactocentric coordinates and velocities
	:param ra: Right ascension [degree]
	:param dec:  Declination [degree]
	:param l: Galactic longitude [degree]
	:param b:  Galactic latitude [degree]
	:param mura: Ra proper motion  [mas/year] (already multiplied for cos(delta))
	:param mudec: Dec proper motion [mas/year]
	:param vrad:  Radial velocity [km/s]
	:param dist:  Distance in kpc o parallax (see below) [kpc or mas]
	:param parallax: if True the dist is in parallax
	:param vlsr: Velocity of the local standard of rest [km/s]
	:param vsun:  3D tuple with the velocity of the Sun in (-U,V,W) [km/s]
	:param zsun: Height of the Sun above the plane [kpc]
	:param rsun: cylindrical radius of the Sun wrt Galactic centre [kpc]
	:param emura:  Error on mura (it could be None)
	:param emudec: Error on mudec (it could be None)
	:param evrad:  Error on vrad (it could be None)
	:param edist: Error on dist (it could be None)
	:return:
		Rsun: Cylindircal radius wrt to the Sun [kpc]
		R: Galactocentric cylindrical radius [kpc]
		Z: Height above the plane [kpc]
		vZ: Z velocity [km/s]
		vR: cylindrical radial velocity [km/s]
		vT: Tangential velocity [km/s]
		if all the errors are not None return also
		eR: error on R [kpc]
		eZ: error on Z [kpc]
		eVx, eVy, eVz: error on velocities  [kpc]
	"""

	if parallax:
		dist_new = ut.parallax_to_distance(dist)
		if edist is not None: edist_new = edist * dist * dist
	else:
		dist_new = dist
		edist_new = edist

	mul, mub = co.pmrapmdec_to_pmllpmbb(mura, mudec, ra, dec, degree=True).T

	xs, ys, zs, vxs, vys, vzs = co.sphergal_to_rectgal(l, b, dist_new, vrad, mul, mub, degree=True).T

	Rs = np.sqrt(xs * xs + ys * ys)

	vsun = np.array([0., vlsr, 0., ]) + np.array(vsun)
	# vsun=(0,0,0)

	R, phi, Z = co.XYZ_to_galcencyl(xs, ys, zs, Zsun=zsun, Xsun=rsun).T

	if edist is not None:
		eR = np.abs(edist_new * np.cos(b * np.pi / 180))
		eZ = np.abs(edist_new * np.sin(b * np.pi / 180))
	else:
		eR = np.nan
		eZ = np.nan

	vR, vT, vZ = co.vxvyvz_to_galcencyl(vxs, vys, vzs, R, phi, Z, vsun=vsun, Xsun=rsun, Zsun=zsun,
										galcen=True).T

	if emura is not None and emudec is not None and evrad is not None and edist is not None:
		covpmrapmdec = np.zeros((len(emura), 2, 2))
		covpmrapmdec[:, 0, 0] = emura
		covpmrapmdec[:, 1, 1] = emudec
		covpmlpmb = co.cov_pmrapmdec_to_pmllpmbb(covpmrapmdec, ra, dec, degree=True)
		covV = co.cov_dvrpmllbb_to_vxyz(dist, edist, evrad, mul, mub, covpmlpmb, l, b, plx=parallax, degree=True)

		eVx, eVy, eVz = covV[:, 0, 0], covV[:, 1, 1], covV[:, 2, 2]
		xg = xs - rsun
		theta = np.arctan2(ys, xg)
		ct = np.cos(theta)
		st = np.sin(theta)
		eVR = np.sqrt(eVx * eVx * ct * ct + eVy * eVy * st * st)
		eVT = np.sqrt(eVx * eVx * st * st + eVy * eVy * ct * ct)

		return Rs, R, Z, vZ, vR, vT, eR, eZ, eVR, eVT, eVz

	return Rs, R, Z, vZ, vR, vT


def _observed_to_physical_werr_core(par, dist_as_parallax=False):
	"""
	Estimate the physical phase space information from the observations
	:param par: a tuple with (id, ra, dec, l, b, dist, edist, mura, emura, mudec, emudec, vra, evrad, Nrandom, Vsunx, Vsuny, Vsunz, Rsun, Vls)
	:return:
	 		A numpy array with dimension (65)
	 		It contains 14 variables with 4 entries excpet the first (id) with only one entry.
	 		For a given variable Var the entries are:
	 			a- Var (median of the Nrandom sampling)
	 			b- Var_error (error on Var, estimated as mad)
	 			c- Var_low (16% percentile of the posterior distribution of Var)
	 			d- Var_up (64% percentile of the posterior distribution of Var)
	 		The variables (and the column number of the respective Var) are:
	 			0- Id: unique Id
	 			1-  Rs: Circular radius wrt to the Sun [kpc]
	 			5-  R: Galactic cylindrical radius [kpc]
	 			9-  Z: Galactic height above the plane [kpc]
	 			13- Vx: Velocity along the Galactic x-axis (pointing toward the Sun) [km/s]
	 			17- Vy: Velocity along the Galactic y-axis (pointing toward the Sun) [km/s]
	 			21- VR: Velocity along the Galactic cylindrical Radius  [km/s]
	 			25- Vz: Velocity along the Galactic z-axis  [km/s]
	 			29- Vr: Velocity along the Galactic radius  [km/s]
	 			33- Vt: Velocity along the Galactic zenithal angle theta  [km/s]
	 			37- Vphi: Velocity along the Galactic azimuthal angle Phi [km/s]
	 			41- Dist: Distane from the Sun [kpc]
	 			45- DistG: Distance from the Galactic centre [km/s]
				49- Phi: Azimuthal angle [deg]
				53- Lz: z-component of angular momentum [kpc * km/s]
				57- L:  angular momentum [kpc * km/s]
				61- Ekin:  kinetic energy [km/s * km/s]
				see the functions (observed_to_physical for further information)
	"""

	id, ra, dec, l, b, dist, edist, mura, emura, mudec, emudec, vrad, evrad, Nrandom, Vsunx, Vsuny, Vsunz, Rsun = par
	Nrandom = int(Nrandom)
	Vsun = (Vsunx, Vsuny, Vsunz)
	onest = np.ones(Nrandom)

	res = np.zeros(shape=(65), dtype=np.float)

	mean = (dist, mura, mudec, vrad)
	std = (edist, emura, emudec, evrad)
	random_values = np.random.normal(mean, std, (Nrandom, 4))
	# cov			          =   np.diag(v=std)
	# random_values            =   np.random.multivariate_normal(mean,cov*cov,Nrandom)
	mul, mub = co.pmrapmdec_to_pmllpmbb(random_values[:, 1], random_values[:, 2], onest * ra, onest * dec,
										degree=True).T

	if dist_as_parallax:
		dist = ut.parallax_to_distance(random_values[:, 0])
		dist = np.where(dist >= 0, dist, np.nan)
	else:
		dist = random_values[:, 0]

	xs, ys, zs, vxs, vys, vzs = co.sphergal_to_rectgal(onest * l, onest * b, dist, random_values[:, 3], mul, mub,
													   degree=True).T
	Rs = np.sqrt(xs * xs + ys * ys)
	R, phi, Z = co.XYZ_to_galcencyl(xs, ys, zs, Zsun=0, Xsun=Rsun).T
	vR, vPhi, vZ = co.vxvyvz_to_galcencyl(vxs, vys, vzs, R, phi, Z, vsun=Vsun, Xsun=Rsun, Zsun=0, galcen=True).T
	theta = np.arctan2(R, Z)  # because in spherical coordiante theta is the angle bwen Z and r
	vr, vt, vp, vx, vy = cylindrical_to_spherical(vR, vPhi, vZ, phi, theta)
	distG = np.sqrt(R * R + Z * Z)
	Lz = R * vPhi
	LR = Z * vPhi
	Lphi = Z * vR - R * vZ
	Ltot = np.sqrt(LR * LR + Lphi * Lphi + Lz * Lz)
	Ekin = 0.5 * (vR * vR + vPhi * vPhi + vZ * vZ)

	res[0] = id
	jj = 1
	res[jj:jj + 2] = mad(Rs, axis=0)
	jj += 2
	res[jj:jj + 2] = np.nanpercentile(Rs, q=(16, 84), axis=0)
	jj += 2
	res[jj:jj + 2] = mad(R, axis=0)
	jj += 2
	res[jj:jj + 2] = np.nanpercentile(R, q=(16, 84), axis=0)
	jj += 2
	res[jj:jj + 2] = mad(Z, axis=0)
	jj += 2
	res[jj:jj + 2] = np.nanpercentile(Z, q=(16, 84), axis=0)
	jj += 2
	res[jj:jj + 2] = mad(vx, axis=0)
	jj += 2
	res[jj:jj + 2] = np.nanpercentile(vx, q=(16, 84), axis=0)
	jj += 2
	res[jj:jj + 2] = mad(vy, axis=0)
	jj += 2
	res[jj:jj + 2] = np.nanpercentile(vy, q=(16, 84), axis=0)
	jj += 2
	res[jj:jj + 2] = mad(vR, axis=0)
	jj += 2
	res[jj:jj + 2] = np.nanpercentile(vR, q=(16, 84), axis=0)
	jj += 2
	res[jj:jj + 2] = mad(vZ, axis=0)
	jj += 2
	res[jj:jj + 2] = np.percentile(vZ, q=(16, 84), axis=0)
	jj += 2
	res[jj:jj + 2] = mad(vr, axis=0)
	jj += 2
	res[jj:jj + 2] = np.nanpercentile(vr, q=(16, 84), axis=0)
	jj += 2
	res[jj:jj + 2] = mad(vt, axis=0)
	jj += 2
	res[jj:jj + 2] = np.nanpercentile(vt, q=(16, 84), axis=0)
	jj += 2
	res[jj:jj + 2] = mad(vPhi, axis=0)
	jj += 2
	res[jj:jj + 2] = np.nanpercentile(vPhi, q=(16, 84), axis=0)
	jj += 2
	res[jj:jj + 2] = mad(dist, axis=0)
	jj += 2
	res[jj:jj + 2] = np.nanpercentile(dist, q=(16, 84), axis=0)
	jj += 2
	res[jj:jj + 2] = mad(distG, axis=0)
	jj += 2
	res[jj:jj + 2] = np.nanpercentile(distG, q=(16, 84), axis=0)
	jj += 2
	phid = phi * 180. / np.pi  # Phi in deg
	res[jj:jj + 2] = mad(phid, axis=0)
	jj += 2
	res[jj:jj + 2] = np.nanpercentile(phid, q=(16, 84), axis=0)
	jj += 2
	res[jj:jj + 2] = mad(Lz, axis=0)
	jj += 2
	res[jj:jj + 2] = np.nanpercentile(Lz, q=(16, 84), axis=0)
	jj += 2
	res[jj:jj + 2] = mad(Ltot, axis=0)
	jj += 2
	res[jj:jj + 2] = np.nanpercentile(Ltot, q=(16, 84), axis=0)
	jj += 2
	res[jj:jj + 2] = mad(Ekin, axis=0)
	jj += 2
	res[jj:jj + 2] = np.nanpercentile(Ekin, q=(16, 84), axis=0)

	return res


def _observed_to_physical_werr_multi(par, dist_as_parallax=False):
	"""
	Estimate the physical phase space information from the observations.
	It is a wrapper to cycle the core function _observed_to_physical_werr_core with a serial for
	:param par: a list of  tuple with (id, ra, dec, l, b, parallax, eparallax, mura, emura, mudec, emudec, vra, evrad, Nrandom, Vsunx, Vsuny, Vsunz, Rsun)
	:return:
	 		A numpy array with dimension (65)
	 		It contains 14 variables with 4 entries excpet the first (id) with only one entry.
	 		For a given variable Var the entries are:
	 			a- Var (median of the Nrandom sampling)
	 			b- Var_error (error on Var, estimated as mad)
	 			c- Var_low (16% percentile of the posterior distribution of Var)
	 			d- Var_up (64% percentile of the posterior distribution of Var)
	 		The variables (and the column number of the respective Var) are:
	 			0- Id: unique Id
	 			1-  Rs: Circular radius wrt to the Sun [kpc]
	 			5-  R: Galactic cylindrical radius [kpc]
	 			9-  Z: Galactic height above the plane [kpc]
	 			13- Vx: Velocity along the Galactic x-axis (pointing toward the Sun) [km/s]
	 			17- Vy: Velocity along the Galactic y-axis (pointing toward the Sun) [km/s]
	 			21- VR: Velocity along the Galactic cylindrical Radius  [km/s]
	 			25- Vz: Velocity along the Galactic z-axis  [km/s]
	 			29- Vr: Velocity along the Galactic radius  [km/s]
	 			33- Vt: Velocity along the Galactic zenithal angle theta  [km/s]
	 			37- Vphi: Velocity along the Galactic azimuthal angle Phi [km/s]
	 			41- Dist: Distane from the Sun [kpc]
	 			45- DistG: Distance from the Galactic centre [km/s]
				49- Phi: Azimuthal angle [deg]
				53- Lz: z-component of angular momentum [kpc * km/s]
				57- L:  angular momentum [kpc * km/s]
				61- Ekin:  kinetic energy [km/s * km/s]
				see the functions (observed_to_physical for further information)
	see the functions (observed_to_physical for further information)
	"""

	res = []

	for i, pari in enumerate(par):
		res.append(_observed_to_physical_werr_core(pari, dist_as_parallax))

	return np.array(res, dtype=np.float)


# TODO: Add also the inclusion of the errors on Galactic parameters
def observed_to_physical_6D_werr(ra, dec, l, b, dist, edist, mura, emura, mudec, emudec, vrad, evrad, source_id=None,
								 Nrandom=1000, Rsun=8.2, Zsun=0, Vlsr=235, Vsun=(-11.1, 12.24, 7.25),
								 dist_as_parallax=False, nproc=2, outfile=None, fitsfile=True, numpyfile=True,
								 asciifile=True):
	"""
	Estimate the physical phase space information from the observations
	:param ra:  Right ascension [degree]
	:param dec: Declination [degree]
	:param l: Galactic longitude [degree]
	:param b: Galactic latitude [degree]
	:param dist:   Distance  [kpc] or [mas] if dist_as_parallax=True
	:param edist:  Distance error  [kpc] or [mas] if dist_as_parallax=True
	:param mura:  Ra proper motion  [mas/year] (already multiplied for cos(delta))
	:param emura: Error on mura  [mas/year]
	:param mudec: Dec proper motion  [mas/year]
	:param emudec: Error on mura  [mas/year]
	:param vrad:  Radial velocity [km/s]
	:param evrad:  Error on vrad  [km/s]
	:param source_id: a key index of each star, if None it is just a counter [None]
	:param Nrandom: Number of points exctracted from a multivariate distribution to estimate the errors
	:param Rsun:  Cylindrical radius of the Sun wrt Galactic centre [8.2 kpc]
	:param Zsun: Cylindrical height of the Sun wrt Galactic plane [0 kpc] (Currently not implemented)
	:param Vlsr: Velocity of the local standard of rest [235 km/s]
	:param Vsun: 3D tuple with the velocity of the Sun in (-U,V,W) [ (-11, 12.24, 7.25) km/s]
	:param dist_as_parallax:  If True consider the dist and edist as parallax and its error
	:param nproc:  Number of threads [2]
	:param outfile: If not None, enable the file output that will have this name
	:param fitsfile: enable the fits output [outfile.fits]
	:param numpyfile: enable the binary numpy output [outfile.npy]
	:param asciifile: enable the  simple txt axii output [outfile.txt]
	:return:
	 		A numpy array with dimension (65)
	 		It contains 14 variables with 4 entries excpet the first (id) with only one entry.
	 		For a given variable Var the entries are:
	 			a- Var (median of the Nrandom sampling)
	 			b- Var_error (error on Var, estimated as mad)
	 			c- Var_low (16% percentile of the posterior distribution of Var)
	 			d- Var_up (64% percentile of the posterior distribution of Var)
	 		The variables (and the column number of the respective Var) are:
	 			0- Id: unique Id
	 			1-  Rs: Circular radius wrt to the Sun [kpc]
	 			5-  R: Galactic cylindrical radius [kpc]
	 			9-  Z: Galactic height above the plane [kpc]
	 			13- Vx: Velocity along the Galactic x-axis (pointing toward the Sun) [km/s]
	 			17- Vy: Velocity along the Galactic y-axis (pointing toward the Sun) [km/s]
	 			21- VR: Velocity along the Galactic cylindrical Radius  [km/s]
	 			25- Vz: Velocity along the Galactic z-axis  [km/s]
	 			29- Vr: Velocity along the Galactic radius  [km/s]
	 			33- Vt: Velocity along the Galactic zenithal angle theta  [km/s]
	 			37- Vphi: Velocity along the Galactic azimuthal angle Phi [km/s]
	 			41- Dist: Distane from the Sun [kpc]
	 			45- DistG: Distance from the Galactic centre [km/s]
				49- Phi: Azimuthal angle [deg]
				53- Lz: z-component of angular momentum [kpc * km/s]
				57- L:  angular momentum [kpc * km/s]
				61- Ekin:  kinetic energy [km/s * km/s]
				see the functions (observed_to_physical for further information)
	"""

	if Zsun != 0:
		raise NotImplementedError('Zsun!=0 not implemented!')

	Nobjects = len(ra)
	onest = np.ones(Nobjects)
	Nrandomlist = onest * Nrandom
	Vsunxlist = onest * Vsun[0]
	Vsunylist = onest * (Vsun[1] + Vlsr)
	Vsunzlist = onest * Vsun[2]
	Rsunlist = onest * Rsun
	if source_id is None: source_id = np.arange(Nobjects)
	datapar = zip(source_id, ra, dec, l, b, dist, edist, mura, emura, mudec, emudec, vrad, evrad, Nrandomlist,
				  Vsunxlist, Vsunylist, Vsunzlist, Rsunlist)

	if nproc == 1:
		t1 = time.time()
		results = _observed_to_physical_werr_multi(datapar)
		t2 = time.time()
	else:
		t1 = time.time()
		_core_func = partial(_observed_to_physical_werr_core, dist_as_parallax=dist_as_parallax)
		with Pool(processes=nproc) as pool:
			results = np.array(pool.map(_core_func, datapar))
		t2 = time.time()

	twork = t2 - t1

	if outfile is not None and (numpyfile or asciifile or fitsfile):

		col_names = (
		'Rs', 'R', 'z', 'Vx', 'Vy', 'VR', 'Vz', 'Vrad', 'Vt', 'Vphi', 'Dist', 'DistG', 'Phi', 'Lz', 'L', 'Ekin')
		subcol_names = ('', '_error', '_low', '_up')
		var_names = ['id', ]
		for col_name in col_names:
			for subcol_name in subcol_names:
				var_names.append(col_name + subcol_name)

		# Numpy binary (pickable) file
		if numpyfile:
			np.save(outfile + '.npy', results, allow_pickle=True, fix_imports=True)

		# Ascii file with header
		if asciifile:
			head = 'Infos:\n  Nobjects= %.5e   Nrandom= %i\n  Rsun= %.3f   zsun= %.3f\n  Vlsr= %.3f   Vsun= (%.3f, %.3f, %.3f)\n  CPU time= %.3f\n' % (
			Nobjects, Nrandom, Rsun, Zsun, Vlsr, Vsun[0], Vsun[1], Vsun[2], twork)
			head += 'SubColumns Legend:\n  a: Median\n  b(_error): Error estimated as mad\n  c(_low): 16% of the posterior\n  d(_up):64% of the posterior\nColumns Legend:\n'
			for i, name in enumerate(var_names):
				if i < 10:
					head += '  %i:  %s \n' % (i, name)
				else:
					head += '  %i: %s \n' % (i, name)

			np.savetxt(outfile + '.txt', results, header=head, fmt='%i' + ' %.3e ' * 64)

		# Fitsfile
		if fitsfile:
			dicf = {}
			for i, name in enumerate(var_names):
				if i == 0:
					dicf[name] = (results[:, i:i + 1], 'K')
				else:
					dicf[name] = (results[:, i:i + 1], 'D')
			ut.make_fits(dicf, outname=outfile + '.fits',
						 header_key={'Nobjects': Nobjects, 'Nrandom': Nrandom, 'Rsun': Rsun, 'zsun': Zsun, 'Vlsr': Vlsr,
									 'Vsunx': Vsun[0], 'Vsuny': Vsun[1], 'Vsunz': Vsun[2]})

	return results


def spherical_to_cartesian_old(Ar, At, Af, theta, phi):
	cost = np.cos(theta)
	sint = np.sin(theta)
	cosf = np.cos(phi)
	sinf = np.sin(phi)

	Ax = Ar * cost * sinf - At * sint + Af * cost * cosf
	Ay = Ar * sint * sinf + At * cost + Af * sint * cosf
	Az = Ar * cosf - Af * sinf

	return Ax, Ay, Az


def cartesian_to_spherical_old(Ax, Ay, Az, theta, phi):
	cost = np.cos(theta)
	sint = np.sin(theta)
	cosf = np.cos(phi)
	sinf = np.sin(phi)

	Ar = Ax * sint * cosf + Ay * sint * sinf + Az * cost
	At = -Ax * cost * cosf + Ay * cost * sinf - Az * sint
	Af = -Ax * sinf + Ay * cosf

	return Ar, At, Af